# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deva.cli.application import Application
    from deva.tools.uv import UV


class Tools:
    def __init__(self, app: Application) -> None:
        self.__app = app

    @cached_property
    def uv(self) -> UV:
        from deva.tools.uv import UV

        return UV(self.__app)
