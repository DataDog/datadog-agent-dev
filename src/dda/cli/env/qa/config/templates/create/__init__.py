# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Create a new Agent config template")
@click.argument("name")
@pass_app
def cmd(app: Application, *, name: str) -> None:
    """
    Create a new Agent config template.
    """
    from dda.env.config.agent import AgentConfigTemplates

    templates = AgentConfigTemplates(app)
    template = templates.get(name)
    if template.exists():
        app.abort(f"Template already exists: {name}")

    template.restore_defaults()
    app.display(f"Template created: {name}")
