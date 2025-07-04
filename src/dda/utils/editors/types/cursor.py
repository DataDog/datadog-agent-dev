# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import Any

from dda.utils.editors.interface import EditorInterface
from dda.utils.fs import Path


class CursorEditorInterface(EditorInterface):
    def open_via_ssh(self, *, server: str, port: int, path: str) -> None:
        self.app.subprocess.run(["cursor", "--remote", f"ssh-remote+root@{server}:{port}", path])

    def add_mcp_server(self, *, name: str, url: str) -> None:
        config = self.__load_mcp_config()
        server_config = self.__get_mcp_server_config(config)
        server_config[name] = {"url": url}
        self.__save_mcp_config(config)

    def remove_mcp_server(self, *, name: str) -> None:
        config = self.__load_mcp_config()
        server_config = self.__get_mcp_server_config(config)
        server_config.pop(name, None)
        self.__save_mcp_config(config)

    @staticmethod
    def __get_mcp_server_config(config: dict[str, Any]) -> dict[str, Any]:
        # https://docs.cursor.com/context/mcp#using-mcp-json
        return config.setdefault("mcpServers", {})

    def __load_mcp_config(self) -> dict[str, Any]:
        import pyjson5

        if not self.__mcp_config_file.is_file():
            return {}

        return pyjson5.decode(self.__mcp_config_file.read_text(encoding="utf-8"))

    def __save_mcp_config(self, config: dict[str, Any]) -> None:
        import json

        self.__mcp_config_file.parent.ensure_dir()
        self.__mcp_config_file.write_text(json.dumps(config, indent=4), encoding="utf-8")

    @cached_property
    def __mcp_config_file(self) -> Path:
        # https://docs.cursor.com/context/mcp#configuration-locations
        return Path.home() / ".cursor" / "mcp.json"
