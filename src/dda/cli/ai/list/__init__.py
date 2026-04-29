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
    from rich.text import Text

    from dda.ai.agent import ACTIVE_PHASES, load_all_sessions, reconcile_session_phase
    from dda.ai.tui import _PHASE_STYLE

    sessions = load_all_sessions(app)
    if not sessions:
        app.display("No agent sessions found.")
        return

    # Reconcile phase for any active sessions so the table reflects reality.
    for s in sessions:
        if s.phase in ACTIVE_PHASES:
            reconcile_session_phase(app, s)

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Phase", no_wrap=True)
    table.add_column("Task")
    table.add_column("Created", no_wrap=True)

    for s in sessions[:10]:
        style = _PHASE_STYLE.get(str(s.phase), "")
        phase_text = Text(str(s.phase).replace("_", " "), style=style)
        created = s.created_at[:19].replace("T", " ")
        table.add_row(
            s.id,
            phase_text,
            s.prompt[:60],
            created,
        )

    app.console.print(table)
