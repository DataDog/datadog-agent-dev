# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import ssl

import httpx
import truststore

from dda.utils.network.http.client import DEFAULT_TIMEOUT, HTTPClient, get_http_client


class TestGetHTTPClient:
    def test_types(self):
        client = get_http_client()
        assert isinstance(client, HTTPClient)
        assert isinstance(client, httpx.Client)

    def test_defaults(self, mocker):
        truststore_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        mock_truststore_context = mocker.patch("truststore.SSLContext", return_value=truststore_context)
        mock_client = mocker.patch("dda.utils.network.http.client.HTTPClient")

        get_http_client()
        mock_truststore_context.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
        mock_client.assert_called_once_with(
            http2=True,
            timeout=DEFAULT_TIMEOUT,
            verify=truststore_context,
        )

    def test_config(self, mocker):
        mock_client = mocker.patch("dda.utils.network.http.client.HTTPClient")

        get_http_client(http2=False, timeout=5, verify=False)
        mock_client.assert_called_once_with(
            http2=False,
            timeout=5,
            verify=False,
        )
