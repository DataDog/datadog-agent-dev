# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING, Self

from deva.utils.platform import PLATFORM_ID
from deva.utils.process import EnvVars

if TYPE_CHECKING:
    from types import TracebackType

    from deva.cli.application import Application
    from deva.utils.fs import Path


class VirtualEnv:
    def __init__(self, path: Path) -> None:
        self.path = path

    if PLATFORM_ID == "windows":

        @cached_property
        def exe_dir(self) -> Path:
            return self.path / "Scripts"

    else:

        @cached_property
        def exe_dir(self) -> Path:
            return self.path / "bin"

    @staticmethod
    def get_sys_path(app: Application) -> list[str]:
        from ast import literal_eval

        output = app.subprocess.capture(["python", "-c", "import sys;print([path for path in sys.path if path])"])
        return literal_eval(output)

    @cached_property
    def __env_vars(self) -> EnvVars:
        old_path = os.environ.get("PATH", os.defpath)
        new_path = f"{self.exe_dir}{os.pathsep}{old_path}"
        return EnvVars(
            {"PATH": new_path, "VIRTUAL_ENV": str(self.path)},
            # The presence of these environment variables is known to cause issues
            exclude=["PYTHONHOME", "__PYVENV_LAUNCHER__"],
        )

    def __enter__(self) -> Self:
        self.__env_vars.__enter__()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        env_vars = self.__env_vars
        # The next context manager should take a new snapshot of the current process' environment variables
        del self.__env_vars
        env_vars.__exit__(exc_type, exc_value, traceback)
