# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Show status of an agent session")
@click.argument("agent_id", required=False, default=None)
@click.option("--logs", "-l", is_flag=True, default=False, help="Print the raw log file instead of parsed output")
@pass_app
def cmd(app: Application, *, agent_id: str | None, logs: bool) -> None:
    """
    Print a snapshot of an agent session.

    If AGENT_ID is omitted and exactly one active session exists, it is used
    automatically. Use `dda ai list` to see all session IDs.

    \b
    Examples:
      dda ai status
      dda ai status abc12345
      dda ai status --logs
      dda ai status abc12345 --logs
    """
    from rich.panel import Panel
    from rich.text import Text

    from dda.ai.agent import find_active_session, load_all_sessions, load_session, reconcile_session_phase
    from dda.ai.runner import _iter_log_events, _parse_event
    from dda.ai.tui import _PHASE_SPINNER, _PHASE_STYLE
    from dda.ai.workspace import run_remote

    if agent_id:
        session = load_session(app, agent_id)
    else:
        session = find_active_session(app)
        if session is None:
            all_sessions = load_all_sessions(app)
            if not all_sessions:
                app.abort("No agent sessions found. Run `dda ai run` to start one.")
            session = all_sessions[0]

    # --- Reconcile phase from remote log, then fetch content for display ---
    reconcile_session_phase(app, session)

    # Concatenate all remote logs in order so the full history is shown,
    # including output from previous runs before any --resume.
    # Fall back to the local log if no remote paths are available.
    if session.remote_log_paths:
        cat_cmd = " ".join(session.remote_log_paths)
        result = run_remote(session.workspace, f"cat {cat_cmd} 2>/dev/null")
        raw_content = result.stdout
    else:
        parts = []
        for lp in session.log_paths:
            p = Path(lp)
            if p.is_file():
                parts.append(p.read_text())
        raw_content = "\n".join(parts)

    # --- Raw log mode ---
    if logs:
        if raw_content:
            app.console.out(raw_content)
        else:
            app.display("No log content available.")
        return

    # --- Header (printed after phase reconciliation so it shows the right phase) ---
    console = app.console

    phase_style = _PHASE_STYLE.get(str(session.phase), "")
    phase_str = str(session.phase).replace("_", " ")
    phase_text = Text()
    if str(session.phase) in _PHASE_SPINNER:
        phase_text.append("⠸ ", style="cyan")
    phase_text.append(phase_str, style=phase_style)

    meta = Text()
    meta.append("dda ai", style="bold")
    meta.append(f"  agent: {session.id}", style="dim")
    meta.append(f"  workspace: {session.workspace}", style="cyan")
    if session.branch:
        meta.append(f"  branch: {session.branch}", style="magenta")
    if session.pr_url:
        meta.append(f"  PR: {session.pr_url}", style="blue underline")
    meta.append("  phase: ")
    meta.append_text(phase_text)
    meta.append(f"\n  task: {session.prompt[:120]}", style="dim")

    console.print(Panel(meta, border_style="bold blue", padding=(0, 1)))

    # --- Claude output (full history) ---
    if raw_content:
        flat: list[str] = []
        for event in _iter_log_events(raw_content):
            try:
                text = _parse_event(event)
            except Exception:  # noqa: BLE001
                continue
            if text:
                flat.extend(text.splitlines())

        if flat:
            log_text = Text(overflow="fold")
            for line in flat:
                log_text.append(line + "\n", style="dim")
            console.print(Panel(log_text, title="[bold]CLAUDE OUTPUT[/bold]", border_style="dim", padding=(0, 1)))
