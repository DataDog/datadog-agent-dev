# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Any, NoReturn

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

    def wait(self, command: list[str], *args: Any, **kwargs: Any) -> None:
        self.app.subprocess.wait(self.format_command(command), *args, **kwargs)

    def run(self, command: list[str], *args: Any, **kwargs: Any) -> CompletedProcess:
        return self.app.subprocess.run(self.format_command(command), *args, **kwargs)

    def capture(self, command: list[str], *args: Any, **kwargs: Any) -> str:
        return self.app.subprocess.capture(self.format_command(command), *args, **kwargs)

    def replace_current_process(self, command: list[str], *args: Any, **kwargs: Any) -> NoReturn:
        self.app.subprocess.replace_current_process(self.format_command(command), *args, **kwargs)
