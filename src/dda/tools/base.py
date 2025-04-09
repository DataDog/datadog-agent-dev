# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, NoReturn

from dda.utils.process import EnvVars

if TYPE_CHECKING:
    from subprocess import CompletedProcess

    from dda.cli.application import Application


class Tool(ABC):
    """
    Base class for all tools. A tool is an executable that may require special
    handling to be executed properly.
    """

    def __init__(self, app: Application) -> None:
        self.__app = app

    @abstractmethod
    def format_command(self, command: list[str]) -> list[str]:
        """
        Format a command to be executed by the tool.

        Parameters:
            command: The command to format.

        Returns:
            The formatted command.
        """

    @property
    def app(self) -> Application:
        """
        The [`Application`][dda.cli.application.Application] instance.
        """
        return self.__app

    def env_vars(self) -> dict[str, str]:  # noqa: PLR6301
        """
        Returns:
            The environment variables to set for the tool.
        """
        return {}

    def run(self, command: list[str], *args: Any, **kwargs: Any) -> CompletedProcess:
        """
        Equivalent to [`SubprocessRunner.run`][dda.utils.process.SubprocessRunner.run] with the `command` formatted
        by the tool's [`format_command`][dda.tools.base.Tool.format_command] method and the environment variables set
        by the tool's [`env_vars`][dda.tools.base.Tool.env_vars] method (if any).

        Parameters:
            command: The command to execute.

        Other parameters:
            *args: Additional arguments to pass to [`SubprocessRunner.run`][dda.utils.process.SubprocessRunner.run].
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.run`][dda.utils.process.SubprocessRunner.run].
        """
        self.__populate_env_vars(kwargs)
        return self.app.subprocess.run(self.format_command(command), *args, **kwargs)

    def capture(self, command: list[str], *args: Any, **kwargs: Any) -> str:
        """
        Equivalent to [`SubprocessRunner.capture`][dda.utils.process.SubprocessRunner.capture] with the `command`
        formatted by the tool's [`format_command`][dda.tools.base.Tool.format_command] method and the environment
        variables set by the tool's [`env_vars`][dda.tools.base.Tool.env_vars] method (if any).

        Parameters:
            command: The command to execute.

        Other parameters:
            *args: Additional arguments to pass to
                [`SubprocessRunner.capture`][dda.utils.process.SubprocessRunner.capture].
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.capture`][dda.utils.process.SubprocessRunner.capture].
        """
        self.__populate_env_vars(kwargs)
        return self.app.subprocess.capture(self.format_command(command), *args, **kwargs)

    def wait(self, command: list[str], *args: Any, **kwargs: Any) -> None:
        """
        Equivalent to [`SubprocessRunner.wait`][dda.utils.process.SubprocessRunner.wait] with the `command` formatted
        by the tool's [`format_command`][dda.tools.base.Tool.format_command] method and the environment variables set
        by the tool's [`env_vars`][dda.tools.base.Tool.env_vars] method (if any).

        Parameters:
            command: The command to execute.

        Other parameters:
            *args: Additional arguments to pass to [`SubprocessRunner.wait`][dda.utils.process.SubprocessRunner.wait].
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.wait`][dda.utils.process.SubprocessRunner.wait].
        """
        self.__populate_env_vars(kwargs)
        self.app.subprocess.wait(self.format_command(command), *args, **kwargs)

    def exit_with(self, command: list[str], *args: Any, **kwargs: Any) -> NoReturn:
        """
        Equivalent to [`SubprocessRunner.exit_with`][dda.utils.process.SubprocessRunner.exit_with]
        with the `command` formatted by the tool's [`format_command`][dda.tools.base.Tool.format_command] method and
        the environment variables set by the tool's [`env_vars`][dda.tools.base.Tool.env_vars] method (if any).

        Parameters:
            command: The command to execute.

        Other parameters:
            *args: Additional arguments to pass to
                [`SubprocessRunner.exit_with`][dda.utils.process.SubprocessRunner.exit_with].
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.exit_with`][dda.utils.process.SubprocessRunner.exit_with].
        """
        self.__populate_env_vars(kwargs)
        self.app.subprocess.exit_with(self.format_command(command), *args, **kwargs)

    def __populate_env_vars(self, kwargs: dict[str, Any]) -> None:
        env_vars = self.env_vars()
        if not env_vars:
            return

        if isinstance(env := kwargs.get("env"), dict):
            for key, value in env_vars.items():
                env.setdefault(key, value)
        else:
            kwargs["env"] = EnvVars(env_vars)
