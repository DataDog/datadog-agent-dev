# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
import time
from functools import cached_property
from typing import TYPE_CHECKING, Any, NoReturn

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.events_api import EventsApi
from datadog_api_client.v1.model.event_create_request import EventCreateRequest

from deva.cli.terminal import Terminal
from deva.config.constants import AppEnvVars

if TYPE_CHECKING:
    from collections.abc import Callable

    from deva.config.file import ConfigFile
    from deva.config.model import RootConfig
    from deva.tools import Tools
    from deva.utils.process import SubprocessRunner


class Application(Terminal):
    def __init__(self, *, terminator: Callable[[int], NoReturn], config_file: ConfigFile, **kwargs: Any) -> None:
        super().__init__(config=config_file.model.terminal, **kwargs)

        self.__terminator = terminator
        self.__config_file = config_file
        self.__start_time = time.perf_counter()

    def abort(self, text: str = "", code: int = 1) -> NoReturn:
        if text:
            self.display_critical(text)
        self.send_telemetry(code)
        self.__terminator(code)

    @cached_property
    def config_file(self) -> ConfigFile:
        return self.__config_file

    @cached_property
    def config(self) -> RootConfig:
        return self.__config_file.model

    @cached_property
    def subprocess(self) -> SubprocessRunner:
        from deva.utils.process import SubprocessRunner

        return SubprocessRunner(self)
    @cached_property
    def tools(self) -> Tools:
        from deva.tools import Tools

        return Tools(self)

    @cached_property
    def dynamic_deps_allowed(self) -> bool:
        return os.getenv(AppEnvVars.NO_DYNAMIC_DEPS) not in {"1", "true"}

    @cached_property
    def managed_installation(self) -> bool:
        return os.getenv("PYAPP") is not None

    def send_telemetry(self, exit_code: int) -> None:
        duration = round(time.perf_counter() - self.__start_time, 1)
        if (
            not self.config_file.data["telemetry"]["user_consent"]
            or not self.config_file.data["telemetry"]["dd_api_key"]
        ):
            return

        body = EventCreateRequest(
            title="Deva command invoked",
            text=f"Command:{sys.argv[1:]} Exit code:{exit_code} Duration:{duration}",
            tags=["cli:deva"],
        )
        config = Configuration(api_key={"apiKeyAuth": self.config_file.data["telemetry"]["dd_api_key"]})
        with ApiClient(config) as api_client:
            api_instance = EventsApi(api_client)
            api_instance.create_event(body=body)
