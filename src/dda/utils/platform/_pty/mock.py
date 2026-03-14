# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import io
import subprocess
import threading
from typing import TYPE_CHECKING, cast

from dda.utils.platform._pty.handle import ThreadedPtyIoHandle
from dda.utils.platform._pty.interface import PtySessionInterface

if TYPE_CHECKING:
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

        self.process = subprocess.Popen(
            [self.executable, *self.args],
            cwd=self.cwd,
            env=self.env,
            encoding=self.encoding,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )

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
        pipe: io.TextIOWrapper = cast(io.TextIOWrapper, self.process.stdout)
        while output := pipe.read(self.READ_CHUNK_SIZE):
            live_writer.write(output)
            live_writer.flush()
            capture_writer.write(output)

    def wait(self) -> None:
        self.process.wait()

    def terminate(self) -> None:
        self.process.terminate()

    def get_exit_code(self) -> int | None:
        return self.process.returncode
