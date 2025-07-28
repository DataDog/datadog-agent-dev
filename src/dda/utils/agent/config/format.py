# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any


def decode_agent_config_file(text: str) -> dict[str, Any]:
    from yaml import safe_load

    return safe_load(text) or {}


def encode_agent_config_file(config: dict[str, Any]) -> str:
    from yaml import safe_dump

    return safe_dump(config, default_flow_style=False)


def decode_agent_integration_config_file(text: str) -> dict[str, Any]:
    from yaml import safe_load

    return safe_load(text) or {}


def agent_config_to_env_vars(config: dict[str, Any]) -> dict[str, str]:
    return dict(sorted(_flatten_config(config).items()))


def _flatten_config(
    config: dict[str, Any],
    prefix: str = "",
    env_vars: dict[str, str] | None = None,
) -> dict[str, str]:
    if env_vars is None:
        env_vars = {}

    for key, value in config.items():
        if value is None:
            continue

        env_key = key.upper().replace("-", "_")
        env_key = f"{prefix}_{env_key}" if prefix else f"DD_{env_key}"

        if isinstance(value, dict):
            _flatten_config(value, env_key, env_vars)
        elif isinstance(value, bool):
            env_vars[env_key] = str(value).lower()
        elif isinstance(value, list | tuple):
            env_vars[env_key] = " ".join(map(str, value))
        else:
            env_vars[env_key] = str(value)

    return env_vars
