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


_CLAUDE_FLAGS = "--print --output-format stream-json --verbose --dangerously-skip-permissions"


def _build_claude_cmd(agent_id: str, prompt: str, repo_path: str) -> str:
    slug = "-".join(prompt.lower().split()[:4]).replace("/", "-")[:40]
    system = SYSTEM_PROMPT.format(agent_id=agent_id, slug=slug)
    full_prompt = f"{system}\n\nTask:\n{prompt}"
    escaped = shlex.quote(full_prompt)
    return f"cd {repo_path} && claude {_CLAUDE_FLAGS} {escaped}"


def _extract_text_from_event(line: str) -> str:
    """
    Parse a Claude stream-json event and return human-readable text.

    Event types we surface:
    - type=assistant, content[].type=text     → the text itself
    - type=assistant, content[].type=tool_use → "⚙ ToolName: key_input_preview"
    - type=user,     content[].type=tool_result with stdout → first line of stdout
    - type=result                              → final result text (already shown above)
    """
    line = line.strip()
    if not line:
        return ""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return ""

    etype = event.get("type", "")

    if etype == "assistant":
        parts = []
        for block in event.get("message", {}).get("content", []):
            btype = block.get("type", "")
            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
            elif btype == "tool_use":
                name = block.get("name", "")
                inp = block.get("input", {})
                # Show the most informative field of the tool input
                preview = (
                    inp.get("command")
                    or inp.get("pattern")
                    or inp.get("file_path")
                    or inp.get("description")
                    or str(inp)[:80]
                )
                parts.append(f"⚙ {name}: {preview}")
        return "\n".join(parts)

    if etype == "user":
        # Show stdout from tool results (first non-empty line, truncated)
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_result":
                tool_result = event.get("tool_use_result", {})
                stdout = tool_result.get("stdout", "").strip()
                if stdout:
                    first_line = stdout.splitlines()[0]
                    return f"  → {first_line[:120]}"

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
    cmd = f"cd {session.repo_path} && claude {_CLAUDE_FLAGS} {escaped}"

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
