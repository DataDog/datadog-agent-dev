# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.github.http import GitHubHTTPClientManager


class GitHub:
    """
    This is available as the [`Application.github`][dda.cli.application.Application.github] property.

    Example usage:

    ```python
    with app.github.http.client() as client:
        client.get("https://api.github.com")
    ```
    """

    def __init__(self, app: Application) -> None:
        self.__app = app

    @cached_property
    def http(self) -> GitHubHTTPClientManager:
        from dda.github.http import GitHubHTTPClientManager

        return GitHubHTTPClientManager(self.__app)
