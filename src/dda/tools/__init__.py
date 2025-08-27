# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.tools.bazel import Bazel
    from dda.tools.docker import Docker
    from dda.tools.git import Git
    from dda.tools.go import Go
    from dda.tools.uv import UV


class Tools:
    """
    This is available as the [`Application.tools`][dda.cli.application.Application.tools] property.
    """

    def __init__(self, app: Application) -> None:
        self.__app = app

    @cached_property
    def bazel(self) -> Bazel:
        from dda.tools.bazel import Bazel

        return Bazel(self.__app)

    @cached_property
    def docker(self) -> Docker:
        from dda.tools.docker import Docker

        return Docker(self.__app)

    @cached_property
    def go(self) -> Go:
        from dda.tools.go import Go

        return Go(self.__app)

    @cached_property
    def uv(self) -> UV:
        from dda.tools.uv import UV

        return UV(self.__app)

    @cached_property
    def git(self) -> Git:
        from dda.tools.git import Git

        return Git(self.__app)
