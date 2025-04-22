# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.utils.fs import Path
    from dda.utils.network.http.client import HTTPClient


class HTTPClientManager:
    """
    A class for managing HTTP clients. This is available as the
    [`Application.http`][dda.cli.application.Application.http] property.
    """

    def __init__(self, app: Application):
        self.__app = app

    def client(self, **kwargs: Any) -> HTTPClient:  # noqa: PLR6301
        """
        Returns:
            An [`HTTPClient`][dda.utils.network.http.client.HTTPClient] instance with proper default configuration.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the
                [`get_http_client`][dda.utils.network.http.client.get_http_client] function.
        """
        from dda.utils.network.http.client import get_http_client

        return get_http_client(**kwargs)

    def download(self, url: str, *, path: Path) -> None:
        with self.client() as client, client.stream("GET", url) as response, path.open(mode="wb", buffering=0) as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
