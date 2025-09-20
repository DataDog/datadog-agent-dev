# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, NoReturn

from msgspec import Struct

from dda.utils.process import EnvVars

if TYPE_CHECKING:
    from collections.abc import Generator
    from subprocess import CompletedProcess

    from dda.cli.application import Application


class ExecutionContext(Struct, frozen=True):
    """
    Configuration for an execution of a tool.
    """

    command: list[str]
    env_vars: dict[str, str]


class Tool(ABC):
    """
    A tool is an external program that may require special handling to be executed properly.
    """

    def __init__(self, app: Application) -> None:
        self.__app = app

    @property
    def app(self) -> Application:
        """
        The [`Application`][dda.cli.application.Application] instance.
        """
        return self.__app

    @contextmanager
    @abstractmethod
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        """
        A context manager bound to the lifecycle of each tool execution.

        Parameters:
            command: The command to execute.

        Yields:
            The execution context.
        """

    def run(self, command: list[str], **kwargs: Any) -> int:
        """
        Equivalent to [`SubprocessRunner.run`][dda.utils.process.SubprocessRunner.run] with the tool's
        [`execution_context`][dda.tools.base.Tool.execution_context] determining the final command and
        environment variables.

        Parameters:
            command: The command to execute.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.run`][dda.utils.process.SubprocessRunner.run].
        """
        with self.execution_context(command) as context:
            _populate_env_vars(kwargs, context.env_vars)
            return self.app.subprocess.run(context.command, **kwargs)

    def capture(self, command: list[str], **kwargs: Any) -> str:
        """
        Equivalent to [`SubprocessRunner.capture`][dda.utils.process.SubprocessRunner.capture] with the tool's
        [`execution_context`][dda.tools.base.Tool.execution_context] determining the final command and
        environment variables.

        Parameters:
            command: The command to execute.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.capture`][dda.utils.process.SubprocessRunner.capture].
        """
        with self.execution_context(command) as context:
            _populate_env_vars(kwargs, context.env_vars)
            return self.app.subprocess.capture(context.command, **kwargs)

    def wait(self, command: list[str], **kwargs: Any) -> None:
        """
        Equivalent to [`SubprocessRunner.wait`][dda.utils.process.SubprocessRunner.wait] with the tool's
        [`execution_context`][dda.tools.base.Tool.execution_context] determining the final command and
        environment variables.

        Parameters:
            command: The command to execute.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.wait`][dda.utils.process.SubprocessRunner.wait].
        """
        with self.execution_context(command) as context:
            _populate_env_vars(kwargs, context.env_vars)
            self.app.subprocess.wait(context.command, **kwargs)

    def exit_with(self, command: list[str], **kwargs: Any) -> NoReturn:
        """
        Equivalent to [`SubprocessRunner.exit_with`][dda.utils.process.SubprocessRunner.exit_with] with the tool's
        [`execution_context`][dda.tools.base.Tool.execution_context] determining the final command and
        environment variables.

        Parameters:
            command: The command to execute.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.exit_with`][dda.utils.process.SubprocessRunner.exit_with].
        """
        with self.execution_context(command) as context:
            _populate_env_vars(kwargs, context.env_vars)
            self.app.subprocess.exit_with(context.command, **kwargs)

    def attach(self, command: list[str], **kwargs: Any) -> CompletedProcess:
        """
        Equivalent to [`SubprocessRunner.attach`][dda.utils.process.SubprocessRunner.attach] with the tool's
        [`execution_context`][dda.tools.base.Tool.execution_context] determining the final command and
        environment variables.

        Parameters:
            command: The command to execute.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.attach`][dda.utils.process.SubprocessRunner.attach].
        """
        with self.execution_context(command) as context:
            _populate_env_vars(kwargs, context.env_vars)
            return self.app.subprocess.attach(context.command, **kwargs)

    def redirect(self, command: list[str], **kwargs: Any) -> CompletedProcess:
        """
        Equivalent to [`SubprocessRunner.redirect`][dda.utils.process.SubprocessRunner.redirect] with the tool's
        [`execution_context`][dda.tools.base.Tool.execution_context] determining the final command and
        environment variables.

        Parameters:
            command: The command to execute.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to
                [`SubprocessRunner.redirect`][dda.utils.process.SubprocessRunner.redirect].
        """
        with self.execution_context(command) as context:
            _populate_env_vars(kwargs, context.env_vars)
            return self.app.subprocess.redirect(context.command, **kwargs)


def _populate_env_vars(kwargs: dict[str, Any], env_vars: dict[str, str]) -> None:
    if not env_vars:
        return

    if isinstance(env := kwargs.get("env"), dict):
        for key, value in env_vars.items():
            env.setdefault(key, value)
    else:
        kwargs["env"] = EnvVars(env_vars)
