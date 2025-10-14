# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.config.model import RootConfig


class User:
    def __init__(self, config: RootConfig) -> None:
        self.__config = config

    @cached_property
    def machine_id(self) -> str:
        from dda.config.constants import AppEnvVars

        if machine_id := os.environ.get(AppEnvVars.TELEMETRY_USER_MACHINE_ID):
            return machine_id

        from dda.utils.platform import get_machine_id

        return str(get_machine_id())

    @cached_property
    def name(self) -> str:
        return self.__config.user.name if self.__config.user.name != "auto" else self.__config.tools.git.author.name

    @cached_property
    def email(self) -> str:
        return self.__config.user.email if self.__config.user.email != "auto" else self.__config.tools.git.author.email
