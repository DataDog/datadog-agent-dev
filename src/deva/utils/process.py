# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from deva.utils.platform import PLATFORM_ID

if TYPE_CHECKING:
    import subprocess
    from types import TracebackType

    from deva.cli.application import Application


class SubprocessRunner:
    def __init__(self, app: Application) -> None:
        self.__app = app

    def run(self, command: list[str] | str, **kwargs: Any) -> subprocess.CompletedProcess:
        import subprocess

        command, kwargs = self.__sanitize_arguments(command, **kwargs)
        check = kwargs.pop("check", True)

        process = subprocess.run(command, **kwargs)  # noqa: PLW1510
        if check and process.returncode:
            if process.stderr or process.stdout:
                # Callers might not want to merge both streams so try stderr first
                self.__app.display_critical(process.stderr or process.stdout)

            self.__app.abort(f"Command failed with exit code {process.returncode}: {command}")

        return process

    def capture(self, command: list[str] | str, *, cross_streams: bool = True, **kwargs: Any) -> str:
        import subprocess

        kwargs.setdefault("encoding", "utf-8")
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT if cross_streams else subprocess.PIPE
        return self.run(command, **kwargs).stdout

    @staticmethod
    def __sanitize_arguments(command: list[str] | str, **kwargs: Any) -> tuple[list[str] | str, dict[str, Any]]:
        if kwargs.get("shell", False):
            return command, kwargs

        if PLATFORM_ID == "windows":
            # Manually locate executables on Windows to avoid multiple cases in which `shell=True` is required:
            #
            # - If the `PATH` environment variable has been modified, see:
            #   https://github.com/python/cpython/issues/52803
            # - Executables that do not have the extension `.exe`, see:
            #   https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw
            if isinstance(command, list):
                import shutil

                executable = command[0]
                command = [shutil.which(executable) or executable, *command[1:]]
        elif isinstance(command, str):
            import shlex

            return shlex.split(command), kwargs

        return command, kwargs


class EnvVars(dict):
    def __init__(
        self,
        env_vars: dict[str, str] | None = None,
        *,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> None:
        super().__init__(os.environ)
        self.old_env = dict(self)

        if include:
            from fnmatch import fnmatch

            self.clear()
            for env_var, value in self.old_env.items():
                for pattern in include:
                    if fnmatch(env_var, pattern):
                        self[env_var] = value
                        break

        if exclude:
            from fnmatch import fnmatch

            for env_var in list(self):
                for pattern in exclude:
                    if fnmatch(env_var, pattern):
                        self.pop(env_var)
                        break

        if env_vars:
            self.update(env_vars)

    def __enter__(self) -> None:
        os.environ.clear()
        os.environ.update(self)

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
