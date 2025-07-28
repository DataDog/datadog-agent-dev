# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dda.env.config.agent import AgentConfig


def get_agent_config_info(agent_config: AgentConfig) -> dict[str, Any]:
    info = {"Config": agent_config.load_scrubbed()}
    integrations_info: dict[str, dict[str, Any]] = {}
    for integration_name, integration_configs in sorted(agent_config.load_integrations().items()):
        integration_ad_config: dict[str, Any] = {}
        integration_config_files: dict[str, dict[str, Any] | str] = {}
        for filename, file_config in integration_configs.items():
            file_info = {}
            if instances := file_config.get("instances", []):
                file_info["Instances"] = len(instances)
            if logs := file_config.get("logs", []):
                file_info["Logs"] = len(logs)

            if filename in {"auto_conf.yaml", "auto_conf.yml"}:
                if ad_identifiers := file_config.get("ad_identifiers", []):
                    file_info["Identifiers"] = ad_identifiers

                integration_ad_config.update(file_info)
                continue

            integration_config_files[str(len(integration_config_files) + 1)] = file_info or "<misconfigured>"

        integration_info: dict[str, Any] = {}
        if integration_ad_config:
            integration_info["Autodiscovery"] = (
                dict(sorted(integration_ad_config.items())) if len(integration_ad_config) > 1 else "<misconfigured>"
            )

        if integration_config_files:
            if len(integration_config_files) == 1:
                integration_info["Config"] = next(iter(integration_config_files.values()))
            else:
                integration_info["Config files"] = integration_config_files

        integrations_info[integration_name] = integration_info

    if integrations_info:
        info["Integrations"] = integrations_info

    return info
