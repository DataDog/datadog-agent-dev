# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import tomlkit

if TYPE_CHECKING:
    from collections.abc import Mapping

    from tomlkit.items import InlineTable

    from deva.utils.fs import Path

SCRUBBED_VALUE = "*****"
SCRUBBED_GLOBS = ("github.auth.token", "orgs.*.api_key", "orgs.*.app_key")


def save_toml_document(document: Mapping, path: Path) -> None:
    path.parent.ensure_dir()
    path.write_atomic(f"{tomlkit.dumps(document).strip()}\n", "w", encoding="utf-8")


def create_toml_document(config: dict[str, Any]) -> InlineTable:
    return tomlkit.item(config)


def scrub_config(config: dict[str, Any]) -> None:
    if "token" in config.get("github", {}).get("auth", {}):
        config["github"]["auth"]["token"] = SCRUBBED_VALUE

    for data in config.get("orgs", {}).values():
        for key in ("api_key", "app_key"):
            if key in data:
                data[key] = SCRUBBED_VALUE
