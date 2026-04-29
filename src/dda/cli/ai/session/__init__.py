# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.ai.agent import AgentSession
    from dda.cli.application import Application


@dynamic_command(short_help="Attach to a running agent session")
@click.argument("agent_id", required=False, default=None)
@pass_app
def cmd(app: Application, *, agent_id: str | None) -> None:
    """
    Attach to an agent session: watch live output and handle confirmations.

    If AGENT_ID is omitted, the most recently active session is used.

    \b
    Interaction:
      - Live Claude output is streamed to the TUI as it arrives.
      - When the agent requests confirmation (e.g. "Push PR?"), you are shown
        the git diff and prompted to confirm or cancel.
      - When the agent finishes you can type a follow-up task to continue on
        the same branch, or press Enter to exit.
      - Press Ctrl+C to detach — Claude keeps running on the remote workspace.

    \b
    Examples:
      dda ai session
      dda ai session abc12345
    """
    from dda.ai.agent import ACTIVE_PHASES, AgentPhase, find_active_session, load_all_sessions, load_session, reconcile_session_phase, save_session
    from dda.ai.runner import start_continuation

    # --- Load session ---
    if agent_id:
        session = load_session(app, agent_id)
    else:
        session = find_active_session(app)
        if session is None:
            all_sessions = load_all_sessions(app)
            if not all_sessions:
                app.abort("No agent sessions found. Run `dda ai run` to start one.")
            session = all_sessions[0]

    # Main loop — runs once per "turn" (initial attach, then once per follow-up)
    while True:
        # Sync phase with remote before attaching
        reconcile_session_phase(app, session)

        if session.phase in ACTIVE_PHASES:
            # Attach live TUI — returns when session reaches a terminal state
            # or when the user detaches with Ctrl+C
            detached = _attach(app, session)
            if detached:
                return
        else:
            # Already done — show static output summary
            _print_summary(app, session)

        # --- Follow-up prompt ---
        if not sys.stdout.isatty():
            break
        try:
            follow_up = input("\nFollow-up task (Enter to exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not follow_up:
            break

        # Start a continuation and loop back to attach to it
        session.prompt = follow_up
        session.phase = AgentPhase.RUNNING
        start_continuation(session, follow_up)
        save_session(app, session)


def _attach(app: Application, session: AgentSession) -> bool:
    """
    Run the interactive TUI for an active session.

    Returns True if the user detached (Ctrl+C) so the caller knows not to
    offer a follow-up prompt.  Returns False when the session reaches a
    terminal state normally.
    """
    from dda.ai.agent import AgentPhase, save_session
    from dda.ai.runner import SENTINEL_AWAITING, SENTINEL_BRANCH, SENTINEL_PR_URL, start_confirmation, tail_session
    from dda.ai.tui import AgentTUI
    from dda.ai.workspace import run_remote

    try:
        with AgentTUI(session) as tui:
            while True:
                pending_text = ""

                for chunk in tail_session(session):
                    pending_text += chunk
                    tui.append_log(chunk)

                    if SENTINEL_BRANCH in pending_text:
                        for line in pending_text.splitlines():
                            if line.startswith(SENTINEL_BRANCH):
                                session.branch = line[len(SENTINEL_BRANCH):].strip()
                                save_session(app, session)
                                tui.update_session(session)

                # --- Claude finished its turn; check what it emitted ---

                if SENTINEL_PR_URL in pending_text:
                    for line in pending_text.splitlines():
                        if line.startswith(SENTINEL_PR_URL):
                            session.pr_url = line[len(SENTINEL_PR_URL):].strip()
                    session.phase = AgentPhase.DONE
                    save_session(app, session)
                    tui.update_session(session)
                    break

                if SENTINEL_AWAITING in pending_text:
                    idx = pending_text.index(SENTINEL_AWAITING)
                    confirm_msg = pending_text[idx + len(SENTINEL_AWAITING):].strip().splitlines()[0]

                    session.phase = AgentPhase.AWAITING_PR_CONFIRM
                    save_session(app, session)
                    tui.update_session(session)
                    tui.set_confirm_prompt(confirm_msg)

                    branch = session.branch or "HEAD"
                    base = "origin/main"
                    commits = run_remote(
                        session.workspace,
                        f"cd {session.repo_path} && git log --oneline {base}...{branch} 2>/dev/null",
                    ).stdout
                    diff = run_remote(
                        session.workspace,
                        f"cd {session.repo_path} && git diff {base}...{branch} 2>/dev/null",
                    ).stdout

                    answer = tui.show_changes_and_prompt(commits, diff, confirm_msg)
                    tui.clear_confirm_prompt()

                    if answer.lower() in {"y", "yes"}:
                        start_confirmation(session, "CONFIRMED")
                        session.phase = AgentPhase.RUNNING
                        save_session(app, session)
                        tui.update_session(session)
                        continue  # restart loop to tail the new log
                    else:
                        session.phase = AgentPhase.CANCELLED
                        save_session(app, session)
                        tui.update_session(session)
                        app.display("Agent cancelled.")
                        return False
                elif pending_text:
                    # Stream ended without any sentinel — mark done
                    if session.phase == AgentPhase.RUNNING:
                        session.phase = AgentPhase.DONE
                        save_session(app, session)
                        tui.update_session(session)
                    break
                # else: empty output from tail (likely a race condition or
                # transient SSH error) — retry on next iteration

    except KeyboardInterrupt:
        app.display(f"\nDetached. Claude is still running on {session.workspace}.")
        app.display(f"Re-attach with: dda ai session {session.id}")
        return True  # detached

    if session.pr_url:
        app.display(f"PR created: {session.pr_url}")
    app.display(f"Agent {session.id} finished.")
    return False


def _print_summary(app: Application, session: AgentSession) -> None:
    """Print a static snapshot of a finished session."""
    from pathlib import Path

    from rich.panel import Panel
    from rich.text import Text

    from dda.ai.runner import _iter_log_events, _parse_event
    from dda.ai.tui import _PHASE_SPINNER, _PHASE_STYLE
    from dda.ai.workspace import run_remote

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

    if session.remote_log_paths:
        cat_cmd = " ".join(session.remote_log_paths)
        raw_content = run_remote(session.workspace, f"cat {cat_cmd} 2>/dev/null").stdout
    else:
        parts = []
        for lp in session.log_paths:
            p = Path(lp)
            if p.is_file():
                parts.append(p.read_text())
        raw_content = "\n".join(parts)

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
