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
from select import select
from typing import TYPE_CHECKING

from dda.utils.platform._pty.interface import PtySessionInterface
from dda.utils.terminal import terminal_size

# https://github.com/python/mypy/issues/19013
assert sys.platform != "win32"  # noqa: S101

if TYPE_CHECKING:
    import io
    import threading
    from types import TracebackType

    from dda.utils.fs import Path


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

    def capture(self, writers: list[io.TextIOWrapper], stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            ready_to_read, _, _ = select([self._fd], [], [], self.READ_INTERVAL_SECONDS)
            if not ready_to_read:
                continue

            try:
                output = os.read(self._fd, self.READ_CHUNK_SIZE)
            except OSError as e:
                if e.errno == errno.EIO:
                    tail = self.decoder.decode(b"", final=True)
                    if tail:
                        for w in writers:
                            w.write(tail)
                            w.flush()
                break
            except KeyboardInterrupt:
                tail = self.decoder.decode(b"", final=True)
                if tail:
                    for w in writers:
                        w.write(tail)
                        w.flush()
                break

            if not output:
                break

            text = self.decoder.decode(output)
            for writer in writers:
                writer.write(text)
                writer.flush()

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
