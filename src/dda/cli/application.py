# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING, Any, NoReturn, Self

from dda.cli.terminal import Terminal
from dda.config.constants import AppEnvVars
from dda.feature_flags.manager import CIFeatureFlagManager, LocalFeatureFlagManager
from dda.utils.ci import running_in_ci

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from dda.config.file import ConfigFile
    from dda.config.model import RootConfig
    from dda.feature_flags.manager import FeatureFlagManager
    from dda.github.core import GitHub
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
    def tools(self) -> Tools:
        from dda.tools import Tools

        return Tools(self)

    @cached_property
    def subprocess(self) -> SubprocessRunner:
        from dda.utils.process import SubprocessRunner

        return SubprocessRunner(self)

    @cached_property
    def http(self) -> HTTPClientManager:
        from dda.utils.network.http.manager import HTTPClientManager

        return HTTPClientManager(self)

    @cached_property
    def github(self) -> GitHub:
        from dda.github.core import GitHub

        return GitHub(self)

    @cached_property
    def telemetry(self) -> TelemetryManager:
        from dda.telemetry.manager import TelemetryManager

        return TelemetryManager(self)

    @cached_property
    def features(self) -> FeatureFlagManager:
        if running_in_ci():
            return CIFeatureFlagManager(self)
        return LocalFeatureFlagManager(self)

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
        from dda.utils.ci import running_in_ci

        if self.telemetry.enabled and self.telemetry.error_state():
            self.display_warning("An error occurred while submitting telemetry.")
            self.display_warning("Check the log: ", end="")
            self.display_info("dda self telemetry log show")
            self.display_warning("Disable telemetry: ", end="")
            self.display_info("dda self telemetry disable")

        update_checker = UpdateChecker(self)
        if not running_in_ci() and self.config.update.mode == "check" and update_checker.ready():
            try:
                new_release = update_checker.new_release()
            except Exception as e:  # noqa: BLE001
                self.display_warning(f"An error occurred while checking for updates: {e}")
            else:
                if new_release is not None:
                    latest_version, release_notes = new_release
                    self.display_warning(f"A new version of dda is available: {latest_version}")
                    self.display_markdown(release_notes)
                    if self.managed_installation:
                        self.display_warning("Run: ", end="")
                        self.display_info("dda self update")

                update_checker.reset()


class UpdateChecker:
    def __init__(self, app: Application) -> None:
        self.__app = app
        self.__timestamp_file = app.config.storage.cache / "last_update_check"

    def ready(self) -> bool:
        if not self.__timestamp_file.is_file():
            return True

        from time import time

        last_check = float(self.__timestamp_file.read_text(encoding="utf-8").strip())
        now = time()

        return now - last_check >= self.__app.config.update.check.get_period_seconds()

    def new_release(self) -> tuple[str, str] | None:
        import httpx
        from packaging.version import Version

        from dda._version import __version__

        current_version = Version(__version__)
        with self.__app.github.http.client(timeout=5) as client:
            try:
                response = client.get("https://api.github.com/repos/DataDog/datadog-agent-dev/releases/latest")
            except httpx.HTTPStatusError as e:
                # Rate limiting
                if e.response.headers.get("Retry-After") is not None:
                    github_auth = self.__app.config.github.auth
                    if not (github_auth.user and github_auth.token):
                        self.__app.display_warning(
                            "The GitHub API rate limit was exceeded while checking for new releases."
                        )
                        self.__app.display_info("Run the following commands to authenticate:")
                        self.__app.display_info("dda config set github.auth.user <user>")
                        self.__app.display_info("dda config set github.auth.token")

                    return None

                raise

            release = response.json()

        latest_version = Version(release["tag_name"].lstrip("v"))
        if latest_version <= current_version:
            return None

        return latest_version.base_version, release["body"]

    def reset(self) -> None:
        from time import time

        self.__timestamp_file.parent.ensure_dir()
        self.__timestamp_file.write_text(str(time()), encoding="utf-8")
