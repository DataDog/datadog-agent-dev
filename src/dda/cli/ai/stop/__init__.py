# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Cancel a running agent session")
@click.argument("agent_id", required=False, default=None)
@pass_app
def cmd(app: Application, *, agent_id: str | None) -> None:
    """
    Cancel a running agent session.

    If AGENT_ID is omitted, cancels the currently active session (if any).
    """
    from dda.ai.agent import ACTIVE_PHASES, AgentPhase, find_active_session, load_session, save_session

    if agent_id:
        session = load_session(app, agent_id)
    else:
        session = find_active_session(app)
        if session is None:
            app.abort("No active agent session found. Use `dda ai list` to see all sessions.")

    if session.phase not in ACTIVE_PHASES:
        app.abort(f"Agent {session.id} is already in a terminal state: {session.phase}")

    session.phase = AgentPhase.CANCELLED
    save_session(app, session)
    app.display(f"Agent [cyan]{session.id}[/cyan] cancelled.")
