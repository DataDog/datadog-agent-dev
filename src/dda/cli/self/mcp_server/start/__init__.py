# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Start the MCP server")
@click.option("--port", type=int, default=9000, help="The port used to run the server")
@pass_app
def cmd(app: Application, *, port: int) -> None:
    """
    Start the MCP server.
    """
    from dda.mcp.manager import MCPManager

    manager = MCPManager(app)
    manager.start(port=port)
