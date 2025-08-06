# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Open the Agent config templates location in your file manager")
@click.argument("name", required=False)
@pass_app
def cmd(app: Application, *, name: str | None) -> None:
    """
    Open the Agent config templates location in your file manager.
    """
    from dda.env.config.agent import AgentConfigTemplates

    templates = AgentConfigTemplates(app)
    if not name:
        default_template = templates.get("default")
        if default_template.exists():
            location = default_template.root_dir
        elif templates.root_dir.is_dir() and (entries := list(templates.root_dir.iterdir())):
            location = entries[0]
        else:
            default_template.restore_defaults()
            location = default_template.root_dir

        click.launch(str(location), locate=True)
        return

    template = templates.get(name)
    if not template.exists():
        app.abort(f"Template not found: {name}")

    click.launch(str(template.path), locate=True)
