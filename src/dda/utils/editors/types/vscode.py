# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import Any

from dda.utils.editors.interface import EditorInterface
from dda.utils.fs import Path


class VSCodeEditorInterface(EditorInterface):
    def open_via_ssh(self, *, server: str, port: int, path: str) -> None:
        self.app.subprocess.run(["code", "--remote", f"ssh-remote+root@{server}:{port}", path])

    def add_mcp_server(self, *, name: str, url: str) -> None:
        config = self.__load_config()
        server_config = self.__get_mcp_server_config(config)
        server_config[name] = {"url": url}
        self.__save_config(config)

    def remove_mcp_server(self, *, name: str) -> None:
        config = self.__load_config()
        server_config = self.__get_mcp_server_config(config)
        server_config.pop(name, None)
        self.__save_config(config)

    @staticmethod
    def __get_mcp_server_config(config: dict[str, Any]) -> dict[str, Any]:
        # https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server-to-your-user-settings
        return config.setdefault("mcp", {}).setdefault("servers", {})

    def __load_config(self) -> dict[str, Any]:
        import pyjson5

        if not self.__config_file.is_file():
            return {}

        return pyjson5.decode(self.__config_file.read_text(encoding="utf-8"))

    def __save_config(self, config: dict[str, Any]) -> None:
        import json

        self.__config_file.parent.ensure_dir()
        self.__config_file.write_text(json.dumps(config, indent=4), encoding="utf-8")

    @cached_property
    def __config_file(self) -> Path:
        # https://code.visualstudio.com/docs/configure/settings#_user-settingsjson-location
        from dda.utils.platform import PLATFORM_ID

        if PLATFORM_ID == "linux":
            from platformdirs import user_config_dir

            app_dir = user_config_dir("Code", appauthor=False)
        else:
            from platformdirs import user_data_dir

            app_dir = user_data_dir("Code", appauthor=False)

        return Path(app_dir) / "User" / "settings.json"
