# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from os import environ

from msgspec import Struct


class OrgConfig(Struct, frozen=True, omit_defaults=True):
    api_key: str = environ.get("DD_API_KEY", "")
    app_key: str = environ.get("DD_APP_KEY", "")
    site: str = environ.get("DD_SITE", "datadoghq.com")
    dd_url: str = environ.get("DD_DD_URL", "https://app.datadoghq.com")
    logs_url: str = environ.get("DD_LOGS_CONFIG_LOGS_DD_URL", "")
