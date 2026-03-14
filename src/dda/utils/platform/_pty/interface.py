# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import io
import os
import shutil
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from types import TracebackType

    from dda.utils.fs import Path
    from dda.utils.platform._pty.handle import PtyIoHandle


class TextWriter(Protocol):
    def write(self, text: str, /) -> object: ...

    def flush(self) -> object: ...


class TextReader(Protocol):
    def read(self, size: int = -1, /) -> str: ...


class PtySessionInterface(ABC):
    READ_INTERVAL_SECONDS = 0.05
    READ_CHUNK_SIZE = io.DEFAULT_BUFFER_SIZE

    def __init__(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None,
        cwd: str | Path | None,
        encoding: str,
    ) -> None:
        self.command = command
        self.env = env
        self.cwd = str(cwd) if cwd else None
        self.encoding = encoding
        self.args = list(command)

        executable = self.args.pop(0)
        executable_path = shutil.which(executable, path=(env or os.environ).get("PATH", os.defpath))
        if not executable_path:
            message = f"Executable not found: {executable}"
            raise RuntimeError(message)
        self.executable = executable_path

    @abstractmethod
    def start_io(
        self,
        live_writer: TextWriter,
        capture_writer: TextWriter,
        *,
        stdin_reader: TextReader | None = None,
    ) -> PtyIoHandle: ...

    @abstractmethod
    def wait(self) -> None: ...

    @abstractmethod
    def terminate(self) -> None: ...

    @abstractmethod
    def get_exit_code(self) -> int | None: ...

    def __enter__(self) -> None: ...

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None: ...
