# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

import winpty

from dda.utils.platform import join_command_args
from dda.utils.platform._pty.interface import PtySessionInterface

# https://github.com/python/mypy/issues/19013
assert sys.platform == "win32"  # noqa: S101

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
        # TODO: Use this once it does something
        # https://github.com/andfoy/pywinpty/issues/510
        encoding: str,
    ) -> None:
        super().__init__(command, env=env, cwd=cwd, encoding=encoding)

        width, height = self.get_terminal_dimensions()
        self.pty = winpty.PTY(width, height)
        self.pty.spawn(
            self.executable,
            cmdline=join_command_args(self.args) if self.args else None,
            cwd=self.cwd,
            env=(
                None
                if self.env is None
                else "\0".join([
                    *(f"{key}={value}" for key, value in self.env.items()),
                    "",
                ])
            ),
        )

    def capture(self, writers: list[io.TextIOWrapper], stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                output = self.pty.read(self.READ_CHUNK_SIZE)
                if not output:
                    time.sleep(self.READ_INTERVAL_SECONDS)
                    continue

                for writer in writers:
                    writer.write(output)
                    writer.flush()
            except winpty.WinptyError:
                if self.pty.iseof():
                    break

                continue

    def wait(self) -> None:
        while self.pty.isalive():
            time.sleep(0.1)

    def terminate(self) -> None:
        import signal

        os.kill(self.pty.pid, signal.SIGTERM)

    def get_exit_code(self) -> int | None:
        return self.pty.get_exitstatus()

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        # https://github.com/andfoy/pywinpty/issues/484
        del self.pty
