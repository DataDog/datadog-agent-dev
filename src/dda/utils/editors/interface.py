# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.cli.application import Application


class EditorInterface(ABC):
    """
    This interface defines the behavior of a code editor.
    """

    def __init__(self, *, app: Application, name: str) -> None:
        self.__app = app
        self.__name = name

    @property
    def app(self) -> Application:
        return self.__app

    @property
    def name(self) -> str:
        return self.__name

    @abstractmethod
    def open_via_ssh(self, *, server: str, port: int, path: str) -> None:
        """
        Open the editor via SSH.

        Parameters:
            server: The server to connect to.
            port: The port to connect to.
            path: The path to the repository to open.
        """

    def add_mcp_server(self, *, name: str, url: str) -> None:
        """
        Add an MCP server to the editor.

        Parameters:
            name: The name of the MCP server.
            url: The URL of the MCP server.
        """
        raise NotImplementedError

    def remove_mcp_server(self, *, name: str) -> None:
        """
        Remove an MCP server from the editor.

        Parameters:
            name: The name of the MCP server.
        """
        raise NotImplementedError
