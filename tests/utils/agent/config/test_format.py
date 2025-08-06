# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.utils.agent.config.format import (
    agent_config_to_env_vars,
    decode_agent_config_file,
    encode_agent_config_file,
)


def test_encode_agent_config_file(helpers):
    assert encode_agent_config_file({
        "api_key": "foobar",
        "extra_tags": ["tag1:value1", "tag2:value2"],
        "proxy": {
            "http": "http://proxy.example.com:8080",
            "https": "https://proxy.example.com:443",
        },
        "hostname_fqdn": True,
        "dogstatsd_port": 8125,
    }) == helpers.dedent(
        """
        api_key: foobar
        dogstatsd_port: 8125
        extra_tags:
        - tag1:value1
        - tag2:value2
        hostname_fqdn: true
        proxy:
          http: http://proxy.example.com:8080
          https: https://proxy.example.com:443
        """
    )


def test_decode_agent_config_file(helpers):
    assert decode_agent_config_file(
        helpers.dedent(
            """
            api_key: foobar
            dogstatsd_port: 8125
            extra_tags:
            - tag1:value1
            - tag2:value2
            hostname_fqdn: true
            proxy:
              http: http://proxy.example.com:8080
              https: https://proxy.example.com:443
            """
        )
    ) == {
        "api_key": "foobar",
        "dogstatsd_port": 8125,
        "extra_tags": ["tag1:value1", "tag2:value2"],
        "hostname_fqdn": True,
        "proxy": {
            "http": "http://proxy.example.com:8080",
            "https": "https://proxy.example.com:443",
        },
    }


def test_agent_config_to_env_vars():
    assert agent_config_to_env_vars({
        "api_key": "foobar",
        "app_key": None,
        "dogstatsd_port": 8125,
        "extra_tags": ["tag1:value1", "tag2:value2"],
        "hostname_fqdn": True,
        "proxy": {
            "http": "http://proxy.example.com:8080",
            "https": "https://proxy.example.com:443",
        },
    }) == {
        "DD_API_KEY": "foobar",
        "DD_DOGSTATSD_PORT": "8125",
        "DD_EXTRA_TAGS": "tag1:value1 tag2:value2",
        "DD_HOSTNAME_FQDN": "true",
        "DD_PROXY_HTTP": "http://proxy.example.com:8080",
        "DD_PROXY_HTTPS": "https://proxy.example.com:443",
    }
