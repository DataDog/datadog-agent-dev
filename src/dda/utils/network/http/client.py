# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import httpx

from dda.utils.retry import DelayedError, FailFastError, wait_for

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_TIMEOUT = 10


def get_http_client(**kwargs: Any) -> HTTPClient:
    """
    Prefer using the [`Application.http`][dda.cli.application.Application.http] property instead.

    ```python
    with app.http.client() as client:
        client.get("https://example.com")
    ```

    Returns:
        An [`HTTPClient`][dda.utils.network.http.client.HTTPClient] instance with proper default configuration.

    Other parameters:
        **kwargs: Additional keyword arguments to pass to the
            [`HTTPClient`][dda.utils.network.http.client.HTTPClient] constructor.
    """
    import ssl

    import truststore

    if "http2" not in kwargs:
        kwargs["http2"] = True
    if "verify" not in kwargs:
        kwargs["verify"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT

    return HTTPClient(**kwargs)


class HTTPClient(httpx.Client):
    """
    A subclass of [`httpx.Client`](https://www.python-httpx.org/api/#client) that intelligently retries requests.

    /// warning
    This class should never be used directly. Instead, use the
    [`get_http_client`][dda.utils.network.http.client.get_http_client] function.
    ///
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__timeout = self.timeout.connect or 0
        # TODO: Manually retry read/write errors eventually rather than only
        # connection errors
        self.timeout.connect = None

    def send(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return wait_for(
            lambda: _get_response(lambda: super(HTTPClient, self).send(*args, **kwargs)),
            timeout=self.__timeout,
        )


def _get_response(sender: Callable[[], httpx.Response]) -> httpx.Response:
    try:
        response = sender()
    except httpx.ConnectError as e:
        if (cause := getattr(e, "__cause__", None)) is not None:
            import httpcore

            if isinstance(cause, httpcore.ConnectError):
                import ssl

                internal_error = cause.args[0]
                if isinstance(internal_error, ssl.SSLCertVerificationError):
                    e.add_note(f"Certificate verification error code: {internal_error.verify_code}")
                    raise FailFastError(e) from None

        raise

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Not idempotent
        if e.request.method == "POST":
            raise FailFastError(e) from None

        # Fail fast on unrecoverable errors
        if (
            response.is_redirect
            or (response.is_client_error and response.status_code not in {408, 429})
            or (response.is_server_error and response.status_code not in {500, 502, 503, 504})
        ):
            raise FailFastError(e) from None

        # Check for rate limiting:
        # https://datatracker.ietf.org/doc/html/rfc7231#section-7.1.3
        if (retry_after := response.headers.get("Retry-After")) is not None:
            # https://datatracker.ietf.org/doc/html/rfc7231#section-7.1.1.1
            if retry_after.isdigit():
                delay = float(retry_after)
            else:
                from dda.utils.date import parse_imf_date

                dt = parse_imf_date(retry_after)
                delay = max(0, dt.timestamp() - time.time())

            raise DelayedError(e, delay=delay) from None

        raise

    return response
