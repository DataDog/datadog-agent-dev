# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import shlex
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from dda.ai.workspace import stream_remote

if TYPE_CHECKING:
    from dda.ai.agent import AgentSession

# Sentinel tokens Claude is instructed to output
SENTINEL_AWAITING = "AWAITING_CONFIRMATION:"
SENTINEL_PR_URL = "PR_URL:"
SENTINEL_BRANCH = "BRANCH:"

SYSTEM_PROMPT = """\
You are an expert Datadog Agent engineer working inside a Datadog workspace.
The datadog-agent repository is checked out at ~/dd/datadog-agent.

Rules:
1. Create a new git branch named: ai/{agent_id}-{slug}
   (slug = first 4 words of the task, lowercase, hyphenated)
2. Implement the task described below.
3. Before finishing: run `dda inv linter.go` and fix all lint errors.
4. Run `dda inv test --targets=<relevant_package>` and fix all test failures.
5. Commit all changes with a clear commit message following the repo conventions.
6. Output EXACTLY this line (and nothing else on that line) when ready:
   BRANCH: <branch-name>
   AWAITING_CONFIRMATION: Code is ready. Push PR?
7. After receiving the message CONFIRMED, run:
   gh pr create --title "<title>" --body "<body>"
   then output the PR URL on a line starting with:
   PR_URL: <url>
8. If asked to fix CI failures, analyze the provided log, push a fix commit,
   then output:
   AWAITING_CONFIRMATION: Fix pushed. Re-check CI?
"""


def _build_claude_cmd(agent_id: str, prompt: str, repo_path: str) -> str:
    slug = "-".join(prompt.lower().split()[:4]).replace("/", "-")[:40]
    system = SYSTEM_PROMPT.format(agent_id=agent_id, slug=slug)
    full_prompt = f"{system}\n\nTask:\n{prompt}"
    escaped = shlex.quote(full_prompt)
    return f"cd {repo_path} && claude --print --output-format stream-json {escaped}"


def _extract_text_from_event(line: str) -> str:
    """Parse a Claude stream-json event line and return visible text, or empty string."""
    line = line.strip()
    if not line:
        return ""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return line  # pass raw line through if not JSON

    etype = event.get("type", "")
    # assistant text delta
    if etype == "content_block_delta":
        delta = event.get("delta", {})
        if delta.get("type") == "text_delta":
            return delta.get("text", "")
    # tool use / result summaries
    if etype == "message_delta":
        return ""
    if etype == "message_stop":
        return ""
    # Fallback: if it's a plain text line (non-JSON upstream), return as-is
    return ""


def stream_claude(session: AgentSession) -> Iterator[str]:
    """
    Stream Claude output lines for the given session.

    Yields visible text chunks. The caller is responsible for detecting
    sentinels (AWAITING_CONFIRMATION, PR_URL, BRANCH) in the yielded text.
    """
    cmd = _build_claude_cmd(session.id, session.prompt, session.repo_path)
    log_file = open(session.log_path, "a", buffering=1)  # noqa: WPS515, SIM115

    try:
        proc = stream_remote(session.workspace, cmd)
        for raw_line in proc.stdout:  # type: ignore[union-attr]
            log_file.write(raw_line)
            log_file.flush()
            text = _extract_text_from_event(raw_line)
            if text:
                yield text
        proc.wait()
        if proc.returncode != 0:
            yield f"\n[claude exited with code {proc.returncode}]\n"
    finally:
        log_file.close()


def send_confirmation(session: AgentSession, message: str) -> Iterator[str]:
    """
    Send a confirmation message to a running Claude session.

    Because we run claude non-interactively, confirmations are implemented
    as a new claude invocation that continues the conversation by reading
    the existing log as context and passing the user's response.
    """
    log_path = Path(session.log_path)
    previous_output = log_path.read_text() if log_path.is_file() else ""

    # Build a continuation prompt
    continuation = (
        f"Previous session output (for context):\n{previous_output[-8000:]}\n\n"
        f"User response: {message}\n\n"
        "Continue from where you left off."
    )
    escaped = shlex.quote(continuation)
    cmd = f"cd {session.repo_path} && claude --print --output-format stream-json {escaped}"

    log_file = open(session.log_path, "a", buffering=1)  # noqa: WPS515, SIM115
    try:
        proc = stream_remote(session.workspace, cmd)
        for raw_line in proc.stdout:  # type: ignore[union-attr]
            log_file.write(raw_line)
            log_file.flush()
            text = _extract_text_from_event(raw_line)
            if text:
                yield text
        proc.wait()
    finally:
        log_file.close()
