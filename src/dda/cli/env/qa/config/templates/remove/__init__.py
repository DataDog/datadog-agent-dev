# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Remove an Agent config template")
@click.argument("name")
@pass_app
def cmd(app: Application, *, name: str) -> None:
    """
    Remove an Agent config template.
    """
    from dda.env.config.agent import AgentConfigTemplates

    templates = AgentConfigTemplates(app)
    template = templates.get(name)
    if not template.exists():
        app.abort(f"Template not found: {name}")

    template.remove()
    app.display(f"Template removed: {name}")
