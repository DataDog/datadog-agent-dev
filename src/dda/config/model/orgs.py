# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from os import environ

from msgspec import Struct


class OrgConfig(Struct, frozen=True, omit_defaults=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [orgs.default]
    api_key = "*****"
    app_key = "*****"
    site = "datadoghq.com"
    dd_url = "https://app.datadoghq.com"
    logs_url = ""
    ```
    ///
    """

    api_key: str = environ.get("DD_API_KEY", "")
    app_key: str = environ.get("DD_APP_KEY", "")
    site: str = environ.get("DD_SITE", "")
    dd_url: str = environ.get("DD_DD_URL", "")
    logs_url: str = environ.get("DD_LOGS_CONFIG_LOGS_DD_URL", "")
