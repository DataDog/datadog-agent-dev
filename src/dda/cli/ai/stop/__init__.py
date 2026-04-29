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
    from dda.ai.workspace import run_remote

    if agent_id:
        session = load_session(app, agent_id)
    else:
        session = find_active_session(app)
        if session is None:
            app.abort("No active agent session found. Use `dda ai list` to see all sessions.")

    if session.phase not in ACTIVE_PHASES:
        app.abort(f"Agent {session.id} is already in a terminal state: {session.phase}")

    # Kill the remote claude process.  The agent runs as:
    #   nohup script -q -c "stty cols ...; claude ..." <logfile>
    # Find the `script` PID that owns our specific log file, then kill its
    # entire process group (script → sh → claude).  Using the process group
    # ensures we never touch unrelated Claude sessions running on the same host.
    if session.remote_log_path:
        log = session.remote_log_path
        kill_cmd = (
            f"pid=$(pgrep -f {log} 2>/dev/null | head -1); "
            f"if [ -n \"$pid\" ]; then "
            f"  pgid=$(ps -o pgid= -p \"$pid\" 2>/dev/null | tr -d ' '); "
            f"  [ -n \"$pgid\" ] && kill -- -\"$pgid\" 2>/dev/null; "
            f"fi; "
            f"true"
        )
        run_remote(session.workspace, kill_cmd)

    session.phase = AgentPhase.CANCELLED
    save_session(app, session)
    app.display(f"Agent {session.id} cancelled.")
