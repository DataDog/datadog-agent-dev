# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Output the location of Agent config templates")
@click.argument("name", required=False)
@pass_app
def cmd(app: Application, *, name: str | None) -> None:
    """
    Output the location of Agent config templates.
    """
    from dda.env.config.agent import AgentConfigTemplates

    templates = AgentConfigTemplates(app)
    if not name:
        if not any(templates):
            templates.get("default").restore_defaults()

        app.display(str(templates.root_dir))
        return

    template = templates.get(name)
    if not template.exists():
        app.abort(f"Template not found: {name}")

    app.display(str(template.root_dir))
