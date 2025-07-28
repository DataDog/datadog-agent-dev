# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dda.cli.application import Application
    from dda.utils.fs import Path


class AgentConfigTemplates:
    def __init__(self, app: Application) -> None:
        self.__app = app

    @cached_property
    def root_dir(self) -> Path:
        return self.__app.config.storage.data / "env" / "config" / "templates"

    def get(self, name: str) -> AgentConfig:
        return AgentConfig(app=self.__app, path=self.root_dir / name)

    def __iter__(self) -> Iterator[AgentConfig]:
        if not self.root_dir.is_dir():
            return

        for path in self.root_dir.iterdir():
            template = AgentConfig(app=self.__app, path=path)
            if template.exists():
                yield template


class AgentConfig:
    def __init__(self, *, app: Application, path: Path) -> None:
        self.__app = app
        self.__root_dir = path

    @cached_property
    def root_dir(self) -> Path:
        return self.__root_dir

    @cached_property
    def integrations_dir(self) -> Path:
        return self.__root_dir / "integrations"

    @cached_property
    def name(self) -> str:
        return self.__root_dir.name

    @cached_property
    def path(self) -> Path:
        return self.__root_dir / "datadog.yaml"

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> dict[str, Any]:
        from dda.utils.agent.config.format import decode_agent_config_file

        config = decode_agent_config_file(self.path.read_text(encoding="utf-8"))
        self.__inherit_org_config(config)
        return dict(sorted(config.items()))

    def load_scrubbed(self) -> dict[str, Any]:
        config = self.load()

        placeholder = "*****"
        for key in ("api_key", "app_key"):
            if key in config:
                config[key] = placeholder

        return config

    def load_integrations(self) -> dict[str, dict[str, dict[str, Any]]]:
        from dda.utils.agent.config.format import decode_agent_integration_config_file

        config: dict[str, dict[str, dict[str, Any]]] = {}
        if not self.integrations_dir.is_dir():
            return config

        for path in sorted(self.integrations_dir.iterdir(), key=lambda p: p.name):
            if not path.is_dir():
                continue

            configs: dict[str, dict[str, Any]] = {
                entry.name: decode_agent_integration_config_file(entry.read_text(encoding="utf-8"))
                for entry in path.iterdir()
                if entry.name.endswith((".yaml", ".yml")) and entry.is_file()
            }
            if configs:
                config[path.name] = dict(sorted(configs.items()))

        return config

    def remove(self) -> None:
        import shutil

        if self.root_dir.is_dir():
            shutil.rmtree(self.root_dir)

    def restore_defaults(self) -> None:
        from dda.utils.agent.config.format import encode_agent_config_file

        config: dict[str, Any] = {}
        self.__inherit_org_config(config)

        self.remove()
        self.root_dir.ensure_dir()
        self.path.write_text(encode_agent_config_file(config), encoding="utf-8")

    def __inherit_org_config(self, config: dict[str, Any]) -> None:
        org_name = config.pop("inherit_org", "default")
        if not org_name:
            return

        org = self.__app.config.orgs[org_name]
        if api_key := (org.api_key or os.environ.get("DD_API_KEY", "")):
            config.setdefault("api_key", api_key)
        if app_key := (org.app_key or os.environ.get("DD_APP_KEY", "")):
            config.setdefault("app_key", app_key)
        if site := (org.site or os.environ.get("DD_SITE", "")):
            config.setdefault("site", site)
        if dd_url := (org.dd_url or os.environ.get("DD_DD_URL", "")):
            config.setdefault("dd_url", dd_url)
        if logs_url := (org.logs_url or os.environ.get("DD_LOGS_CONFIG_LOGS_DD_URL", "")):
            config.setdefault("logs_config", {}).setdefault("logs_dd_url", logs_url)
