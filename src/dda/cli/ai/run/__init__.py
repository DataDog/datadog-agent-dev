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
@click.option("--resume", "resume_id", default=None, help="Resume an existing session (agent ID) with a new prompt")
@pass_app
def cmd(
    app: Application,
    *,
    workspace: str,
    prompt_text: str | None,
    plan_file: str | None,
    jira_id: str | None,
    repo: str,
    resume_id: str | None,
) -> None:
    """
    Start a Claude AI agent on WORKSPACE (runs in the background).

    The agent starts immediately and runs detached — use ``dda ai session``
    to attach, watch live output, and handle confirmations.

    Provide the task via one of: --prompt, --plan, or --jira.
    Use --resume <agent-id> to continue an existing session on the same branch.

    \b
    Examples:
      dda ai run workspace-kevinf-dd-agent --prompt "Add OOM-kill metric"
      dda ai run workspace-kevinf-dd-agent --plan tasks/my-feature.md
      dda ai run workspace-kevinf-dd-agent --jira DDAI-4321
      dda ai run workspace-kevinf-dd-agent --resume abc12345 --prompt "Also add unit tests"
    """
    from dda.ai.agent import AgentPhase, create_session, find_active_session, load_session, save_session
    from dda.ai.runner import start_continuation, start_new_session
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

    if resume_id:
        # --- Continue an existing session ---
        session = load_session(app, resume_id)
        session.prompt = prompt
        session.phase = AgentPhase.RUNNING
        start_continuation(session, prompt)  # updates session.remote_log_paths
        save_session(app, session)
        app.display(
            f"Continuation started for agent {session.id}"
            + (f" on branch {session.branch}" if session.branch else "")
        )
    else:
        # --- Guard: no concurrent agents ---
        active = find_active_session(app)
        if active:
            app.abort(
                f"An agent is already active (id={active.id}, phase={active.phase}). "
                "Use `dda ai stop` to cancel it first."
            )

        # --- Check workspace connectivity ---
        app.display_waiting(f"Checking connection to '{workspace}'...")
        if not test_connection(workspace):
            app.abort(f"Cannot reach workspace '{workspace}' via SSH. Check the name and your SSH config.")

        # --- Create session and launch ---
        session = create_session(app, workspace, prompt)
        session.repo_path = repo
        session.phase = AgentPhase.RUNNING
        start_new_session(session)
        save_session(app, session)
        app.display(f"Agent {session.id} started on {workspace}")

    app.display(f"Attach with: dda ai session {session.id}")
