# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.config.model.storage import StorageDirs
    from dda.utils.fs import Path


class MCPManager:
    def __init__(self, app: Application) -> None:
        self.__app = app

    def start(self, *, port: int) -> None:
        import json

        from dda.cli.base import ensure_features_installed

        if self.__pid_file.is_file():
            self.__app.abort("MCP server is already running")

        ensure_features_installed(["mcp"], app=self.__app)

        self.__logging_config_file.write_text(json.dumps(self.__logging_config), encoding="utf-8")
        pid = self.__app.subprocess.spawn_daemon([
            sys.executable,
            "-m",
            "pycli_mcp",
            "dda.cli:dda",
            "--debug",
            "--port",
            str(port),
            "--log-config",
            str(self.__logging_config_file),
        ])
        self.__pid_file.write_text(str(pid), encoding="utf-8")

    def stop(self) -> None:
        if not self.__pid_file.is_file():
            self.__app.display_warning("MCP server is not running")
            return

        import psutil

        pid = int(self.__pid_file.read_text().strip())
        try:
            process = psutil.Process(pid)
            process.kill()
        except psutil.NoSuchProcess:
            self.__app.display_warning("MCP server is not running")

        self.__pid_file.unlink()

    def status(self) -> None:
        if not self.__pid_file.is_file():
            self.__app.display_warning("MCP server is not running")
            return

        import psutil

        pid = int(self.__pid_file.read_text().strip())
        try:
            process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            self.__app.display_warning("MCP server is not running")
        else:
            if process.is_running():
                self.__app.display_success("MCP server is running")
            else:
                self.__app.display_warning("MCP server is not running")

    def show_log(self) -> None:
        if not self.__log_file.is_file():
            self.__app.display_warning("No logs available")
            return

        import shutil
        import sys

        with self.__log_file.open(encoding="utf-8") as f:
            shutil.copyfileobj(f, sys.stdout)

    @cached_property
    def __pid_file(self) -> Path:
        return self.__storage_dir.data / "server.pid"

    @cached_property
    def __log_file(self) -> Path:
        return self.__storage_dir.cache / "server.log"

    @cached_property
    def __logging_config_file(self) -> Path:
        return self.__storage_dir.cache / "logging.json"

    @cached_property
    def __logging_config(self) -> dict[str, Any]:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "defaultFormatter": {
                    "format": "%(asctime)s %(levelname)-8s %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "fileHandler": {
                    "class": "logging.FileHandler",
                    "filename": str(self.__log_file),
                    "mode": "w",
                    "formatter": "defaultFormatter",
                    "level": "DEBUG",
                }
            },
            "root": {
                "handlers": ["fileHandler"],
                "level": "DEBUG",
            },
        }

    @cached_property
    def __storage_dir(self) -> StorageDirs:
        dirs = self.__app.config.storage.join("mcp")
        dirs.data.ensure_dir()
        dirs.cache.ensure_dir()
        return dirs
