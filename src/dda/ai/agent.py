# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

import msgspec

if TYPE_CHECKING:
    from dda.cli.application import Application


class AgentPhase(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_PR_CONFIRM = "awaiting_pr_confirm"
    MONITORING_CI = "monitoring_ci"
    AWAITING_CI_FIX_CONFIRM = "awaiting_ci_fix_confirm"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_PHASES = {
    AgentPhase.CREATED,
    AgentPhase.RUNNING,
    AgentPhase.AWAITING_PR_CONFIRM,
    AgentPhase.MONITORING_CI,
    AgentPhase.AWAITING_CI_FIX_CONFIRM,
}


class AgentSession(msgspec.Struct, frozen=False):
    id: str
    workspace: str
    phase: AgentPhase
    prompt: str
    created_at: str
    updated_at: str
    branch: str = ""
    pr_url: str = ""
    log_paths: list = []  # local logs in chronological order (one per invocation)
    remote_log_paths: list = []  # remote logs in chronological order (one per invocation)
    repo_path: str = "~/dd/datadog-agent"

    @property
    def log_path(self) -> str:
        """The current (most recent) local log path."""
        return self.log_paths[-1] if self.log_paths else ""

    @property
    def remote_log_path(self) -> str:
        """The current (most recent) remote log path."""
        return self.remote_log_paths[-1] if self.remote_log_paths else ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace": self.workspace,
            "phase": str(self.phase),
            "prompt": self.prompt,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "branch": self.branch,
            "pr_url": self.pr_url,
            "log_paths": list(self.log_paths),
            "remote_log_paths": list(self.remote_log_paths),
            "repo_path": self.repo_path,
        }


def _storage_dir(app: Application) -> Path:
    path = Path(app.config.storage.join("ai").data)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _session_path(storage: Path, agent_id: str) -> Path:
    return storage / f"{agent_id}.json"


def create_session(app: Application, workspace: str, prompt: str) -> AgentSession:
    storage = _storage_dir(app)
    agent_id = uuid.uuid4().hex[:8]
    now = datetime.now(UTC).isoformat()
    local_log = str(storage / f"{agent_id}.log")
    remote_log = f"/tmp/dda-ai-{agent_id}.log"
    session = AgentSession(
        id=agent_id,
        workspace=workspace,
        phase=AgentPhase.CREATED,
        prompt=prompt,
        created_at=now,
        updated_at=now,
        log_paths=[local_log],
        remote_log_paths=[remote_log],
    )
    save_session(app, session)
    return session


def save_session(app: Application, session: AgentSession) -> None:
    storage = _storage_dir(app)
    session.updated_at = datetime.now(UTC).isoformat()
    _session_path(storage, session.id).write_text(json.dumps(session.to_dict(), indent=2))


def _migrate_session_data(data: dict) -> dict:
    """Migrate old session JSON formats to current schema."""
    # Old: single log_path string → new: log_paths list
    if "log_path" in data and "log_paths" not in data:
        old = data.pop("log_path")
        data["log_paths"] = [old] if old else []
    else:
        data.pop("log_path", None)
    # Old: single remote_log_path string → new: remote_log_paths list
    if "remote_log_path" in data and "remote_log_paths" not in data:
        old = data.pop("remote_log_path")
        data["remote_log_paths"] = [old] if old else []
    else:
        data.pop("remote_log_path", None)
    return data


def load_session(app: Application, agent_id: str) -> AgentSession:
    storage = _storage_dir(app)
    path = _session_path(storage, agent_id)
    if not path.is_file():
        app.abort(f"No agent session found with id: {agent_id}")
    data = _migrate_session_data(json.loads(path.read_text()))
    return msgspec.convert(data, AgentSession)


def load_all_sessions(app: Application) -> list[AgentSession]:
    storage = _storage_dir(app)
    sessions = []
    for p in sorted(storage.glob("*.json")):
        try:
            data = _migrate_session_data(json.loads(p.read_text()))
            sessions.append(msgspec.convert(data, AgentSession))
        except Exception:  # noqa: BLE001
            continue
    return sorted(sessions, key=lambda s: s.created_at, reverse=True)


def find_active_session(app: Application) -> AgentSession | None:
    for session in load_all_sessions(app):
        if session.phase in ACTIVE_PHASES:
            return session
    return None


def reconcile_session_phase(app: Application, session: AgentSession) -> None:
    """
    Read the **latest** remote log and update the session phase to reflect
    what Claude has actually done since the last local observation.

    Only the latest log is scanned — previous logs may contain stale sentinels
    from earlier turns (e.g. an old AWAITING_CONFIRMATION that was already
    confirmed) and must not influence the current phase.

    Detects:
    - ``AWAITING_CONFIRMATION:`` sentinel → phase becomes AWAITING_PR_CONFIRM
    - ``type=result`` event without AWAITING → phase becomes DONE
    """
    from dda.ai.runner import SENTINEL_AWAITING, _iter_log_events, _parse_event
    from dda.ai.workspace import run_remote

    if session.phase not in ACTIVE_PHASES or not session.remote_log_paths:
        return

    # Only read the latest log to avoid false positives from previous turns.
    result = run_remote(session.workspace, f"cat {session.remote_log_path} 2>/dev/null")
    raw_content = result.stdout
    if not raw_content:
        return

    saw_result = False
    saw_awaiting = False

    for event in _iter_log_events(raw_content):
        if not isinstance(event, dict):
            continue

        if event.get("type") == "result":
            saw_result = True

        try:
            text = _parse_event(event)
        except Exception:  # noqa: BLE001
            text = ""
        if text and SENTINEL_AWAITING in text:
            saw_awaiting = True

    new_phase = session.phase
    if saw_awaiting:
        new_phase = AgentPhase.AWAITING_PR_CONFIRM
    elif saw_result:
        new_phase = AgentPhase.DONE
    else:
        # No result event found — check if the remote process is still alive.
        # If it's dead (no pgrep match on the log file), Claude crashed or was
        # killed without emitting a result event.  Mark done.
        log = session.remote_log_path
        check = run_remote(session.workspace, f"pgrep -f {log} >/dev/null 2>&1 && echo alive || echo dead")
        if check.stdout.strip() == "dead":
            new_phase = AgentPhase.DONE

    if new_phase != session.phase:
        session.phase = new_phase
        save_session(app, session)
