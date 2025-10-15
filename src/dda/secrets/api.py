# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os

import keyring

from dda.config.constants import AppEnvVars

KEYRING_SERVICE = "dda"
KEYRING_ITEM_API_KEY = "telemetry_api_key"
KEYRING_ITEM_CLIENT_TOKEN = "feature_flags_client_token"  # noqa: S105 This is not a hardcoded secret but the linter complains on it


def read_api_key() -> str | None:
    if (api_key := os.environ.get(AppEnvVars.TELEMETRY_API_KEY)) is not None:
        return api_key

    return keyring.get_password(KEYRING_SERVICE, KEYRING_ITEM_API_KEY)


def read_client_token() -> str | None:
    if (client_token := os.environ.get(AppEnvVars.FEATURE_FLAGS_CLIENT_TOKEN)) is not None:
        return client_token

    return keyring.get_password(KEYRING_SERVICE, KEYRING_ITEM_CLIENT_TOKEN)


def save_api_key(api_key: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_ITEM_API_KEY, api_key)


def save_client_token(client_token: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_ITEM_CLIENT_TOKEN, client_token)


def fetch_api_key() -> str:
    from dda.secrets.vault import fetch_secret

    return fetch_secret("group/subproduct-agent/deva", "telemetry-api-key")


def fetch_client_token() -> str:
    from dda.secrets.vault import fetch_secret

    return fetch_secret("group/subproduct-agent/deva", "feature-flags-client-token")
