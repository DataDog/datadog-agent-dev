# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Any, NoReturn

from dda.utils.process import EnvVars

if TYPE_CHECKING:
    from subprocess import CompletedProcess

    from dda.cli.application import Application


class Tool(ABC):
    def __init__(self, app: Application) -> None:
        self.__app = app

    @abstractmethod
    def format_command(self, command: list[str]) -> list[str]:
        """Return the formatted command."""

    @cached_property
    def app(self) -> Application:
        return self.__app

    def env_vars(self) -> dict[str, str]:  # noqa: PLR6301
        return {}

    def wait(self, command: list[str], *args: Any, **kwargs: Any) -> None:
        self.__populate_env_vars(kwargs)
        self.app.subprocess.wait(self.format_command(command), *args, **kwargs)

    def run(self, command: list[str], *args: Any, **kwargs: Any) -> CompletedProcess:
        self.__populate_env_vars(kwargs)
        return self.app.subprocess.run(self.format_command(command), *args, **kwargs)

    def capture(self, command: list[str], *args: Any, **kwargs: Any) -> str:
        self.__populate_env_vars(kwargs)
        return self.app.subprocess.capture(self.format_command(command), *args, **kwargs)

    def exit_with_command(self, command: list[str], *args: Any, **kwargs: Any) -> NoReturn:
        self.__populate_env_vars(kwargs)
        self.app.subprocess.exit_with_command(self.format_command(command), *args, **kwargs)

    def __populate_env_vars(self, kwargs: dict[str, Any]) -> None:
        env_vars = self.env_vars()
        if not env_vars:
            return

        if isinstance(env := kwargs.get("env"), dict):
            for key, value in env_vars.items():
                env.setdefault(key, value)
        else:
            kwargs["env"] = EnvVars(env_vars)
