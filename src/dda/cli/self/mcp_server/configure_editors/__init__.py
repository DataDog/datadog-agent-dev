# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Configure MCP server for all editors", hidden=True)
@pass_app
def cmd(app: Application) -> None:
    """
    Configure MCP server for all editors.
    """
    from dda.utils.editors import AVAILABLE_EDITORS, get_editor

    for editor_type in AVAILABLE_EDITORS:
        editor = get_editor(editor_type)(app=app, name=editor_type)
        try:
            editor.add_mcp_server(name="dda", url="http://localhost:9000/mcp/")
        except NotImplementedError:
            app.display_warning(f"Editor `{editor_type}` does not support MCP servers")
