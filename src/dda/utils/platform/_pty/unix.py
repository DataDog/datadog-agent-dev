# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import codecs
import errno
import os
import pty
import subprocess
import sys
import termios
import threading
from contextlib import suppress
from select import select
from typing import TYPE_CHECKING

from dda.utils.platform._pty.handle import ThreadedPtyIoHandle
from dda.utils.platform._pty.interface import PtySessionInterface
from dda.utils.terminal import terminal_size

# https://github.com/python/mypy/issues/19013
assert sys.platform != "win32"  # noqa: S101

if TYPE_CHECKING:
    from types import TracebackType

    from dda.utils.fs import Path
    from dda.utils.platform._pty.handle import PtyIoHandle
    from dda.utils.platform._pty.interface import TextReader, TextWriter


class PtySession(PtySessionInterface):
    def __init__(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None,
        cwd: str | Path | None,
        encoding: str,
    ) -> None:
        super().__init__(command, env=env, cwd=cwd, encoding=encoding)

        fd, child_fd = pty.openpty()
        self._fd: int | None = fd
        self._fd_lock = threading.Lock()
        os.set_inheritable(self._fd, False)
        os.set_inheritable(child_fd, True)

        width, height = terminal_size()
        termios.tcsetwinsize(self._fd, (height, width))

        self.process = subprocess.Popen(
            [self.executable, *self.args],
            cwd=self.cwd,
            env=self.env,
            stdout=child_fd,
            stderr=child_fd,
            pass_fds=(child_fd,),
        )
        os.close(child_fd)

        # Manually decode because wrapping the PTY fd with an `open` in text
        # mode causes immediate errors when reading on Linux for some reason,
        # even though it works fine on macOS.
        self.decoder = codecs.getincrementaldecoder(self.encoding)()

    def start_io(
        self,
        live_writer: TextWriter,
        capture_writer: TextWriter,
        *,
        stdin_reader: TextReader | None = None,
    ) -> PtyIoHandle:
        _ = stdin_reader
        stop_event = threading.Event()
        return ThreadedPtyIoHandle(
            lambda: self._drain_output(live_writer, capture_writer),
            stop_event=stop_event,
            cancel_reader=self._close_fd,
        )

    def _drain_output(self, live_writer: TextWriter, capture_writer: TextWriter) -> None:
        try:
            self._drain_output_body(live_writer, capture_writer)
        finally:
            capture_writer.flush()

    def _drain_output_body(self, live_writer: TextWriter, capture_writer: TextWriter) -> None:
        while True:
            fd = self._get_fd()
            if fd is None:
                break

            try:
                ready_to_read, _, _ = select([fd], [], [], self.READ_INTERVAL_SECONDS)
            except OSError as e:
                # `EBADF` means the PTY fd is no longer valid.
                # If cancellation closed it while `select()` was waiting, exit cleanly.
                if e.errno == errno.EBADF and self._get_fd() is None:
                    break

                raise

            if not ready_to_read:
                continue

            try:
                output = os.read(fd, self.READ_CHUNK_SIZE)
            except OSError as e:
                # `EIO` means the PTY stream reached end-of-file on Unix.
                # Flush any decoder tail before leaving the read loop.
                if e.errno == errno.EIO:
                    tail = self.decoder.decode(b"", final=True)
                    if tail:
                        live_writer.write(tail)
                        live_writer.flush()
                        capture_writer.write(tail)
                # If cancellation closed it during `os.read()`, treat that as normal shutdown.
                elif e.errno == errno.EBADF and self._get_fd() is None:
                    break
                break
            except KeyboardInterrupt:
                tail = self.decoder.decode(b"", final=True)
                if tail:
                    live_writer.write(tail)
                    live_writer.flush()
                    capture_writer.write(tail)
                break

            if not output:
                break

            text = self.decoder.decode(output)
            live_writer.write(text)
            live_writer.flush()
            capture_writer.write(text)

    def wait(self) -> None:
        self.process.wait()

    def terminate(self) -> None:
        self.process.terminate()

    def get_exit_code(self) -> int | None:
        return self.process.returncode

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self._close_fd()

    def _get_fd(self) -> int | None:
        with self._fd_lock:
            return self._fd

    def _close_fd(self) -> None:
        with self._fd_lock:
            fd = self._fd
            self._fd = None

        if fd is not None:
            with suppress(OSError):
                os.close(fd)
