# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os

import keyring

from dda.config.constants import AppEnvVars

KEYRING_SERVICE = "dda"
KEYRING_ITEM_API_KEY = "telemetry_api_key"


def read_api_key() -> str | None:
    if (api_key := os.environ.get(AppEnvVars.TELEMETRY_API_KEY)) is not None:
        return api_key

    return keyring.get_password(KEYRING_SERVICE, KEYRING_ITEM_API_KEY)


def save_api_key(api_key: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_ITEM_API_KEY, api_key)


def fetch_api_key() -> str:
    from dda.telemetry.vault import fetch_secret

    return fetch_secret("group/subproduct-agent/deva", "telemetry-api-key")
