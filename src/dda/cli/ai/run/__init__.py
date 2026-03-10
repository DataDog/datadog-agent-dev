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


@dynamic_command(short_help="Start a Claude agent on a workspace")
@click.argument("workspace")
@click.option("--prompt", "-p", "prompt_text", default=None, help="Inline task description")
@click.option("--plan", "plan_file", default=None, type=click.Path(exists=True), help="Path to a Markdown plan file")
@click.option("--jira", "jira_id", default=None, help="Jira ticket ID (e.g. DDAI-123)")
@click.option("--repo", default="~/dd/datadog-agent", show_default=True, help="Repo path on the workspace")
@pass_app
def cmd(
    app: Application,
    *,
    workspace: str,
    prompt_text: str | None,
    plan_file: str | None,
    jira_id: str | None,
    repo: str,
) -> None:
    """
    Start a Claude AI agent on WORKSPACE.

    Provide the task via one of: --prompt, --plan, or --jira.

    \b
    Examples:
      dda ai run workspace-kevinf-dd-agent --prompt "Add OOM-kill metric"
      dda ai run workspace-kevinf-dd-agent --plan tasks/my-feature.md
      dda ai run workspace-kevinf-dd-agent --jira DDAI-4321
    """
    from dda.ai.agent import AgentPhase, create_session, find_active_session, save_session
    from dda.ai.runner import SENTINEL_AWAITING, SENTINEL_BRANCH, SENTINEL_PR_URL, stream_claude
    from dda.ai.tui import AgentTUI
    from dda.ai.workspace import test_connection

    # --- Resolve prompt ---
    inputs = [x for x in [prompt_text, plan_file, jira_id] if x is not None]
    if len(inputs) == 0:
        app.abort("Provide exactly one of --prompt, --plan, or --jira")
    if len(inputs) > 1:
        app.abort("Provide exactly one of --prompt, --plan, or --jira (got multiple)")

    if plan_file:
        prompt = Path(plan_file).read_text()
    elif jira_id:
        prompt = f"Implement the task described in Jira ticket {jira_id}."
    else:
        prompt = prompt_text  # type: ignore[assignment]

    # --- Guard: no concurrent agents ---
    active = find_active_session(app)
    if active:
        app.abort(
            f"An agent is already active (id={active.id}, phase={active.phase}). "
            "Use `dda ai stop` to cancel it first."
        )

    # --- Check workspace connectivity ---
    app.display_waiting(f"Checking connection to workspace '{workspace}'...")
    if not test_connection(workspace):
        app.abort(f"Cannot reach workspace '{workspace}' via SSH. Check the name and your SSH config.")

    # --- Create session ---
    session = create_session(app, workspace, prompt)
    session.repo_path = repo
    session.phase = AgentPhase.RUNNING
    save_session(app, session)

    app.display(f"[bold]Agent {session.id}[/bold] started on [cyan]{workspace}[/cyan]")

    # --- Run TUI + stream Claude ---
    pending_text = ""

    with AgentTUI(session, console=app.console) as tui:
        for chunk in stream_claude(session):
            pending_text += chunk
            tui.append_log(chunk)

            # Parse sentinels
            if SENTINEL_BRANCH in pending_text:
                for line in pending_text.splitlines():
                    if line.startswith(SENTINEL_BRANCH):
                        session.branch = line[len(SENTINEL_BRANCH):].strip()
                        save_session(app, session)
                        tui.update_session(session)

            if SENTINEL_AWAITING in pending_text:
                # Extract the message after the sentinel
                idx = pending_text.index(SENTINEL_AWAITING)
                confirm_msg = pending_text[idx + len(SENTINEL_AWAITING):].strip().splitlines()[0]

                session.phase = AgentPhase.AWAITING_PR_CONFIRM
                save_session(app, session)
                tui.update_session(session)
                tui.set_confirm_prompt(confirm_msg)

                answer = tui.prompt_user(confirm_msg)
                tui.clear_confirm_prompt()
                pending_text = ""

                if answer.lower() in {"y", "yes"}:
                    # Continue Claude with CONFIRMED
                    from dda.ai.runner import send_confirmation

                    session.phase = AgentPhase.RUNNING
                    save_session(app, session)
                    tui.update_session(session)

                    for chunk in send_confirmation(session, "CONFIRMED"):
                        pending_text += chunk
                        tui.append_log(chunk)

                        if SENTINEL_PR_URL in pending_text:
                            for line in pending_text.splitlines():
                                if line.startswith(SENTINEL_PR_URL):
                                    session.pr_url = line[len(SENTINEL_PR_URL):].strip()
                                    session.phase = AgentPhase.DONE
                                    save_session(app, session)
                                    tui.update_session(session)
                            break
                else:
                    session.phase = AgentPhase.CANCELLED
                    save_session(app, session)
                    tui.update_session(session)
                    app.display("\nAgent cancelled.")
                    return

        # Claude stream ended without an explicit AWAITING — mark done if no error
        if session.phase == AgentPhase.RUNNING:
            session.phase = AgentPhase.DONE
            save_session(app, session)
            tui.update_session(session)

    if session.pr_url:
        app.display(f"\n[green]PR created:[/green] {session.pr_url}")
    app.display(f"[green]Agent {session.id} finished.[/green]")
