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


@dynamic_command(short_help="Show Agent config template details")
@click.argument("name", required=False)
@pass_app
def cmd(app: Application, *, name: str | None) -> None:
    """
    Show Agent config template details.
    """
    from dda.cli.env.qa.config.utils import get_agent_config_info
    from dda.env.config.agent import AgentConfigTemplates

    templates = AgentConfigTemplates(app)
    if not name:
        existing_templates = list(templates)
        if existing_templates:
            app.display_table({template.name: get_agent_config_info(template) for template in existing_templates})
            return

        default_template = templates.get("default")
        default_template.restore_defaults()
        app.display_table({default_template.name: get_agent_config_info(default_template)})
        return

    template = templates.get(name)
    if not template.exists():
        app.abort(f"Template not found: {name}")

    app.display_table(get_agent_config_info(template))
