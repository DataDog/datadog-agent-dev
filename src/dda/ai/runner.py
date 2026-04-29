# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import re
import shlex
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from dda.ai.workspace import start_remote_bg, stream_remote

# Strip ANSI/VT100 escape sequences and carriage returns introduced by the
# remote pseudo-TTY (script -q allocates one to force line-buffered output).
_CONTROL_RE = re.compile(r"\x1b(?:\[[0-9;?]*[a-zA-Z]|[()][012AB]|[DEFONM78])|\r")


def _clean(line: str) -> str:
    return _CONTROL_RE.sub("", line)


def _iter_log_events(raw_content: str):
    """
    Yield parsed JSON dicts from a stream-json log, handling PTY line-wrap.

    When ``script`` runs with a narrow PTY width (default 80 cols), long JSON
    event lines are wrapped with newlines.  This function accumulates wrapped
    fragments back into complete JSON objects before parsing.
    """
    buffer = ""
    for raw_line in raw_content.splitlines():
        fragment = _clean(raw_line).strip()
        if not fragment:
            continue
        # A line starting with '{' signals a new JSON event.
        # Flush any accumulated buffer first.
        if fragment.startswith("{") and buffer:
            try:
                yield json.loads(buffer)
            except json.JSONDecodeError:
                pass
            buffer = fragment
        else:
            buffer += fragment
    if buffer:
        try:
            yield json.loads(buffer)
        except json.JSONDecodeError:
            pass


if TYPE_CHECKING:
    from dda.ai.agent import AgentSession

# Sentinel tokens Claude is instructed to output
SENTINEL_AWAITING = "AWAITING_CONFIRMATION:"
SENTINEL_PR_URL = "PR_URL:"
SENTINEL_BRANCH = "BRANCH:"

# ---------------------------------------------------------------------------
# Prompt building blocks — shared across all invocation types
# ---------------------------------------------------------------------------

_IDENTITY = """\
You are an expert Datadog Agent engineer working inside a Datadog workspace.
The datadog-agent repository is checked out at ~/dd/datadog-agent.
ALWAYS READ ALL RULES BEFORE YOU START WORKING.\
"""

_QUALITY_RULES = """\
- If you encounter error with the expected path, like invoke task not working, simple git commands not working, or anything else. Do not try to hack the system so it works, just output:
  AWAITING_CONFIRMATION: I encountered an error with the expected path. Please help me.
- Before finishing: run `dda inv linter.go` and fix all lint errors.
- Run `dda inv test --targets=<relevant_package>` and fix all test failures.
- Commit all changes with a clear commit message following the repo conventions.
- You should never bypass failing pre-commit hooks. You can skip pre-push hooks for now because they are not working in workspaces
- If you do not know what should be your next move, explain the issue you encounter and ask for help by outputting:
  AWAITING_CONFIRMATION: I don't know what to do next. Please help me.\
"""

_SENTINEL_RULES = """\
- When code is ready, output EXACTLY these two lines (nothing else on those lines):
  BRANCH: <branch-name>
  AWAITING_CONFIRMATION: Code is ready. Push PR?
- After receiving CONFIRMED, run:
  gh pr create --draft --title "<title>" --body "<body>"
  then output the PR URL on a line starting with:
  PR_URL: <url>
- If asked to fix CI failures, analyze the provided log, push a fix commit, then output:
  AWAITING_CONFIRMATION: Fix pushed. Re-check CI?
- If you need to do operations that can be dangerous, always ask for confirmation first, by outputting:
  AWAITING_CONFIRMATION: Do you want to proceed with the operation?\
"""


def _extract_log_summary(log_paths: list[str], max_chars: int = 4000) -> str:
    """
    Return a human-readable summary across all local log files by extracting
    text from parsed stream-json events.  Much more compact than raw log bytes.
    """
    lines: list[str] = []
    for lp in log_paths:
        p = Path(lp)
        if not p.is_file():
            continue
        raw = p.read_text()
        for event in _iter_log_events(raw):
            try:
                text = _parse_event(event)
            except Exception:  # noqa: BLE001
                continue
            if text:
                lines.append(text)
    summary = "\n".join(lines)
    # Trim from the start so we keep the most recent context
    return summary[-max_chars:] if len(summary) > max_chars else summary


def _new_session_prompt(agent_id: str, prompt: str) -> str:
    slug = "-".join(prompt.lower().split()[:4]).replace("/", "-")[:40]
    return f"""{_IDENTITY}

Branch setup:
1. git checkout main && git pull
2. Create a new branch named: kfairise/{agent_id}-{slug}
   (slug = first 4 words of the task, lowercase, hyphenated)

Quality rules:
{_QUALITY_RULES}

Output protocol:
{_SENTINEL_RULES}

Task:
{prompt}"""


def _continuation_prompt(session: AgentSession, new_prompt: str) -> str:
    branch_line = f"branch `{session.branch}`" if session.branch else "the current branch"
    context = _extract_log_summary(session.log_paths)
    context_section = f"\nWhat was done so far:\n{context}\n" if context else ""
    return f"""{_IDENTITY}

You are continuing work on {branch_line}.
Original task: {session.prompt}
{context_section}
Branch rules:
- Stay on {branch_line}. Do NOT create a new branch or checkout main.

Quality rules:
{_QUALITY_RULES}

Output protocol:
{_SENTINEL_RULES}

New task:
{new_prompt}"""


def _confirmation_prompt(session: AgentSession, message: str) -> str:
    branch_line = f"branch `{session.branch}`" if session.branch else "the current branch"
    context = _extract_log_summary(session.log_paths)
    context_section = f"\nWhat was done so far:\n{context}\n" if context else ""
    return f"""{_IDENTITY}

You are continuing work on {branch_line}.
Original task: {session.prompt}
{context_section}
Branch rules:
- Stay on {branch_line}. Do NOT create a new branch or checkout main.

Quality rules:
{_QUALITY_RULES}

Output protocol:
{_SENTINEL_RULES}

User response: {message}

Continue from where you left off."""


# ---------------------------------------------------------------------------
# Start helpers — launch a Claude process remotely, do NOT tail
# ---------------------------------------------------------------------------

_CLAUDE_FLAGS = "--print --output-format stream-json --verbose --dangerously-skip-permissions"


def _new_log_paths(session: AgentSession, suffix: str = "") -> None:
    """Allocate a new pair of local + remote log paths for a new invocation.

    Appends to both ``session.log_paths`` and ``session.remote_log_paths`` so
    every Claude invocation gets its own isolated log files.
    """
    run_id = uuid.uuid4().hex[:6]
    tag = f"-{suffix}" if suffix else ""

    # Derive local dir from the first local log path
    local_dir = Path(session.log_paths[0]).parent if session.log_paths else Path("/tmp")
    local = str(local_dir / f"{session.id}{tag}-{run_id}.log")
    remote = f"/tmp/dda-ai-{session.id}{tag}-{run_id}.log"

    session.log_paths = list(session.log_paths) + [local]
    session.remote_log_paths = list(session.remote_log_paths) + [remote]


def start_new_session(session: AgentSession) -> None:
    """Launch Claude for a brand-new session. Does not tail output."""
    prompt = _new_session_prompt(session.id, session.prompt)
    cmd = f"cd {session.repo_path} && claude {_CLAUDE_FLAGS} {shlex.quote(prompt)}"
    start_remote_bg(session.workspace, cmd, session.remote_log_path)


def start_continuation(session: AgentSession, new_prompt: str) -> None:
    """Launch Claude to continue an existing session on the same branch.

    Updates ``session.remote_log_paths`` with the new log path before launching
    so callers can save the session immediately after.
    """
    _new_log_paths(session, "cont")
    prompt = _continuation_prompt(session, new_prompt)
    cmd = f"cd {session.repo_path} && claude {_CLAUDE_FLAGS} {shlex.quote(prompt)}"
    start_remote_bg(session.workspace, cmd, session.remote_log_path)


def start_confirmation(session: AgentSession, message: str) -> None:
    """Launch Claude to process a user confirmation (y/n or free text).

    Updates ``session.remote_log_paths`` with the new log path before launching.
    """
    _new_log_paths(session, "conf")
    prompt = _confirmation_prompt(session, message)
    cmd = f"cd {session.repo_path} && claude {_CLAUDE_FLAGS} {shlex.quote(prompt)}"
    start_remote_bg(session.workspace, cmd, session.remote_log_path)


# ---------------------------------------------------------------------------
# Tail helper — stream an already-running session's current log
# ---------------------------------------------------------------------------

def tail_session(session: AgentSession) -> Iterator[str]:
    """
    Tail the current remote log of a session, yielding human-readable text.

    Stops automatically when a ``result`` event signals Claude has finished its
    current turn.  If the caller stops iterating early (e.g. KeyboardInterrupt),
    only the local tail process is killed — Claude keeps running remotely.
    """
    proc = stream_remote(session.workspace, f"tail --retry -n +1 -f {session.remote_log_path}")
    log_file = open(session.log_path, "a", buffering=1)  # noqa: WPS515, SIM115
    try:
        for raw_line in proc.stdout:  # type: ignore[union-attr]
            line = _clean(raw_line)
            log_file.write(line)
            log_file.flush()
            text = _extract_text_from_event(line)
            if text:
                yield text
            try:
                event = json.loads(line.strip())
                if isinstance(event, dict) and event.get("type") == "result":
                    break
            except json.JSONDecodeError:
                pass
    finally:
        proc.terminate()
        proc.wait()
        log_file.close()


# ---------------------------------------------------------------------------
# Convenience wrappers (start + tail in one call)
# ---------------------------------------------------------------------------

def stream_claude(session: AgentSession) -> Iterator[str]:
    """Start a new session and immediately tail it."""
    start_new_session(session)
    yield from tail_session(session)


def stream_continuation(session: AgentSession, new_prompt: str) -> Iterator[str]:
    """Start a continuation and immediately tail it."""
    start_continuation(session, new_prompt)
    yield from tail_session(session)


# ---------------------------------------------------------------------------
# Event parsing
# ---------------------------------------------------------------------------

def _extract_text_from_event(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return ""
    if not isinstance(event, dict):
        return ""
    try:
        return _parse_event(event)
    except Exception:  # noqa: BLE001
        return ""


def _parse_event(event: dict) -> str:
    etype = event.get("type", "")

    if etype == "assistant":
        parts = []
        for block in event.get("message", {}).get("content", []):
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
            elif btype == "tool_use":
                name = block.get("name", "")
                inp = block.get("input", {})
                if not isinstance(inp, dict):
                    inp = {}
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
        tool_result = event.get("tool_use_result", {})
        if isinstance(tool_result, dict):
            stdout = tool_result.get("stdout", "").strip()
            if stdout:
                first_line = stdout.splitlines()[0]
                return f"  → {first_line[:120]}"

    return ""
