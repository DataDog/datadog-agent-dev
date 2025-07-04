# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING, Any, NoReturn, Self

from dda.cli.terminal import Terminal
from dda.config.constants import AppEnvVars

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from dda.config.file import ConfigFile
    from dda.config.model import RootConfig
    from dda.telemetry.manager import TelemetryManager
    from dda.tools import Tools
    from dda.utils.network.http.manager import HTTPClientManager
    from dda.utils.process import SubprocessRunner


class Application(Terminal):
    """
    This class is never imported directly.
    Instead, use the `dda.cli.base.pass_app` decorator to pass an instance of this class to your command.

    ```python
    from __future__ import annotations

    from typing import TYPE_CHECKING

    from dda.cli.base import dynamic_command, pass_app

    if TYPE_CHECKING:
        from dda.cli.application import Application


    @dynamic_command(short_help="Some command")
    @pass_app
    def cmd(app: Application) -> None:
        \"""
        Long description of the command.
        \"""
        app.display_waiting("Running some command")
    ```
    """

    def __init__(self, *, terminator: Callable[[int], NoReturn], config_file: ConfigFile, **kwargs: Any) -> None:
        super().__init__(config=config_file.model.terminal, **kwargs)

        self.__terminator = terminator
        self.__config_file = config_file

    def abort(self, text: str = "", code: int = 1) -> NoReturn:
        """
        Gracefully terminate the application with an optional
        [error message][dda.cli.application.Application.display_critical]. The message is
        appended to the [last error message][dda.cli.application.Application.last_error].

        Parameters:
            text: The error message to display.
            code: The exit code to use.
        """
        if text:
            self.last_error += text
            self.display_critical(text)

        self.__terminator(code)

    @cached_property
    def last_error(self) -> str:
        """
        The last recorded error message which will be collected as telemetry. This can be overwritten like so:

        ```python
        app.last_error = "An error occurred"
        ```

        Alternatively, you can append to it:

        ```python
        app.last_error += "\\nExtra information or context"
        ```
        """
        return ""

    @cached_property
    def config_file(self) -> ConfigFile:
        return self.__config_file

    @cached_property
    def config(self) -> RootConfig:
        return self.__config_file.model

    @cached_property
    def subprocess(self) -> SubprocessRunner:
        from dda.utils.process import SubprocessRunner

        return SubprocessRunner(self)

    @cached_property
    def http(self) -> HTTPClientManager:
        from dda.utils.network.http.manager import HTTPClientManager

        return HTTPClientManager(self)

    @cached_property
    def tools(self) -> Tools:
        from dda.tools import Tools

        return Tools(self)

    @cached_property
    def telemetry(self) -> TelemetryManager:
        from dda.telemetry.manager import TelemetryManager

        return TelemetryManager(self)

    @cached_property
    def dynamic_deps_allowed(self) -> bool:
        return os.getenv(AppEnvVars.NO_DYNAMIC_DEPS) not in {"1", "true"}

    @cached_property
    def managed_installation(self) -> bool:
        return os.getenv("PYAPP") is not None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self.telemetry.error_state():
            self.display_warning("An error occurred while submitting telemetry.")
            self.display_warning("Check the log: ", end="")
            self.display_info("dda self telemetry log show")
            self.display_warning("Disable telemetry: ", end="")
            self.display_info("dda self telemetry disable")
