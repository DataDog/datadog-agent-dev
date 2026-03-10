# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Show live status of an agent session")
@click.argument("agent_id", required=False, default=None)
@pass_app
def cmd(app: Application, *, agent_id: str | None) -> None:
    """
    Show the live TUI for an agent session.

    If AGENT_ID is omitted and exactly one active session exists, it is used
    automatically. Use `dda ai list` to see all session IDs.
    """
    from dda.ai.agent import find_active_session, load_all_sessions, load_session
    from dda.ai.tui import AgentTUI

    if agent_id:
        session = load_session(app, agent_id)
    else:
        session = find_active_session(app)
        if session is None:
            # Fall back to most recent session
            all_sessions = load_all_sessions(app)
            if not all_sessions:
                app.abort("No agent sessions found. Run `dda ai run` to start one.")
            session = all_sessions[0]

    log_path = Path(session.log_path)

    with AgentTUI(session, console=app.console) as tui:
        # Replay existing log
        if log_path.is_file():
            for line in log_path.read_text().splitlines():
                tui.append_log(line)

        # Tail new lines if still active
        from dda.ai.agent import ACTIVE_PHASES

        if session.phase not in ACTIVE_PHASES:
            # Session finished — just display static view, then exit
            time.sleep(2)
            return

        # Watch for new log lines and session state changes
        seen_size = log_path.stat().st_size if log_path.is_file() else 0
        try:
            while True:
                # Reload session state
                from dda.ai.agent import load_session as _reload

                session = _reload(app, session.id)
                tui.update_session(session)

                if session.phase not in ACTIVE_PHASES:
                    time.sleep(1)
                    return

                # Read new log content
                if log_path.is_file():
                    current_size = log_path.stat().st_size
                    if current_size > seen_size:
                        with log_path.open() as f:
                            f.seek(seen_size)
                            new_content = f.read()
                        for line in new_content.splitlines():
                            tui.append_log(line)
                        seen_size = current_size

                # Surface awaiting confirmation
                if session.phase.startswith("awaiting"):
                    msg = "Agent is awaiting confirmation. Run `dda ai run` to interact."
                    tui.set_confirm_prompt(msg)

                time.sleep(1)
        except KeyboardInterrupt:
            pass
