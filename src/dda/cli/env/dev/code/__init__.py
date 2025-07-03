# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.cli.env.dev.utils import option_env_type
from dda.utils.editors import AVAILABLE_EDITORS

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Open a code editor for the developer environment")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.option("--repo", "-r", help="The Datadog repository to work on")
@click.option(
    "--editor",
    "-e",
    "editor_name",
    type=click.Choice(AVAILABLE_EDITORS),
    help="The editor to use, overriding any configured editor",
)
@click.option("--configure-mcp", is_flag=True, hidden=True, help="Enable MCP server for all editors")
@pass_app
def cmd(
    app: Application,
    *,
    env_type: str,
    instance: str,
    repo: str | None,
    editor_name: str | None,
    configure_mcp: bool,
) -> None:
    """
    Open a code editor for the developer environment.
    """
    from dda.env.dev import get_dev_env
    from dda.env.models import EnvironmentState
    from dda.utils.editors import get_editor

    if configure_mcp:
        for editor_type in AVAILABLE_EDITORS:
            editor = get_editor(editor_type)(app=app, name=editor_type)
            try:
                editor.add_mcp_server(name="dda", url="http://localhost:9000/mcp/")
            except NotImplementedError:
                app.display_warning(f"Editor `{editor_type}` does not support MCP servers")

        return

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    status = env.status()
    expected_state = EnvironmentState.STARTED
    if status.state != expected_state:
        app.abort(f"Developer environment `{env_type}` is in state `{status.state}`, must be `{expected_state}`")

    editor_type = editor_name or app.config.env.dev.editor
    editor = get_editor(editor_type)(app=app, name=editor_type)
    env.code(editor=editor, repo=repo)
