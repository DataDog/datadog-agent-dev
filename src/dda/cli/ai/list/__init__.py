# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="List all agent sessions")
@pass_app
def cmd(app: Application) -> None:
    """
    List all agent sessions with their current status.
    """
    from rich.table import Table

    from dda.ai.agent import load_all_sessions

    sessions = load_all_sessions(app)
    if not sessions:
        app.display("No agent sessions found.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Workspace")
    table.add_column("Phase")
    table.add_column("Branch", style="magenta")
    table.add_column("PR", style="blue")
    table.add_column("Created")

    _PHASE_STYLE = {
        "running": "cyan",
        "awaiting_pr_confirm": "yellow",
        "monitoring_ci": "blue",
        "awaiting_ci_fix_confirm": "yellow",
        "done": "green",
        "failed": "red",
        "cancelled": "dim",
        "created": "dim",
    }

    for s in sessions:
        style = _PHASE_STYLE.get(str(s.phase), "")
        created = s.created_at[:19].replace("T", " ")
        table.add_row(
            s.id,
            s.workspace,
            f"[{style}]{s.phase}[/{style}]" if style else str(s.phase),
            s.branch or "-",
            s.pr_url or "-",
            created,
        )

    app.console.print(table)
