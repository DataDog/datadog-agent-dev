# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import io
import subprocess
from typing import TYPE_CHECKING, cast

from dda.utils.platform._pty.interface import PtySessionInterface

if TYPE_CHECKING:
    import threading

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

        self.process = subprocess.Popen(
            [self.executable, *self.args],
            cwd=self.cwd,
            env=self.env,
            encoding=self.encoding,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )

    def capture(self, writers: list[io.TextIOWrapper], stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            pipe: io.TextIOWrapper = cast(io.TextIOWrapper, self.process.stdout)
            output = pipe.read(self.READ_CHUNK_SIZE)
            if not output:
                break

            for writer in writers:
                writer.write(output)
                writer.flush()

    def wait(self) -> None:
        self.process.wait()

    def terminate(self) -> None:
        self.process.terminate()

    def get_exit_code(self) -> int | None:
        return self.process.returncode
