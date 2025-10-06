# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import ssl
from typing import TYPE_CHECKING

import truststore

from dda.utils.network.http.client import DEFAULT_TIMEOUT

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from dda.cli.application import Application
    from dda.config.file import ConfigFile


class TestHTTP:
    def test_no_auth(self, app: Application, mocker: MockerFixture) -> None:
        truststore_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        mock_truststore_context = mocker.patch("truststore.SSLContext", return_value=truststore_context)
        mock_client = mocker.patch("dda.utils.network.http.client.HTTPClient")

        app.github.http.client()
        mock_truststore_context.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
        mock_client.assert_called_once_with(
            http2=True,
            timeout=DEFAULT_TIMEOUT,
            verify=truststore_context,
        )

    def test_auth(self, app: Application, config_file: ConfigFile, mocker: MockerFixture) -> None:
        config_file.data["github"]["auth"] = {"user": "foo", "token": "bar"}
        config_file.save()

        truststore_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        mock_truststore_context = mocker.patch("truststore.SSLContext", return_value=truststore_context)
        mock_client = mocker.patch("dda.utils.network.http.client.HTTPClient")

        app.github.http.client()
        mock_truststore_context.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
        mock_client.assert_called_once_with(
            http2=True,
            timeout=DEFAULT_TIMEOUT,
            verify=truststore_context,
            auth=("foo", "bar"),
        )
