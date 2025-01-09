# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING, Any, NoReturn

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

    def abort(self, text: str = "", code: int = 1) -> NoReturn:
        if text:
            self.display_critical(text)

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
