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

        self._fd, child_fd = pty.openpty()
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

        # Manually decode because wrapping the master fd with an `open` in text
        # mode causes immediate errors when reading on Linux for some reason,
        # even though it works fine on macOS
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
        )

    def _drain_output(self, live_writer: TextWriter, capture_writer: TextWriter) -> None:
        try:
            self._drain_output_body(live_writer, capture_writer)
        finally:
            capture_writer.flush()

    def _drain_output_body(self, live_writer: TextWriter, capture_writer: TextWriter) -> None:
        while True:
            ready_to_read, _, _ = select([self._fd], [], [], self.READ_INTERVAL_SECONDS)
            if not ready_to_read:
                continue

            try:
                output = os.read(self._fd, self.READ_CHUNK_SIZE)
            except OSError as e:
                if e.errno == errno.EIO:
                    tail = self.decoder.decode(b"", final=True)
                    if tail:
                        live_writer.write(tail)
                        live_writer.flush()
                        capture_writer.write(tail)
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
        os.close(self._fd)
