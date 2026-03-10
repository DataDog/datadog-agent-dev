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
    log_path: str = ""
    repo_path: str = "~/dd/datadog-agent"

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
            "log_path": self.log_path,
            "repo_path": self.repo_path,
        }


def _storage_dir(app: Application) -> Path:
    path = Path(app.config.storage.join("ai").data)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _session_path(storage: Path, agent_id: str) -> Path:
    return storage / f"{agent_id}.json"


def _log_path(storage: Path, agent_id: str) -> Path:
    return storage / f"{agent_id}.log"


def create_session(app: Application, workspace: str, prompt: str) -> AgentSession:
    storage = _storage_dir(app)
    agent_id = uuid.uuid4().hex[:8]
    now = datetime.now(UTC).isoformat()
    log = str(_log_path(storage, agent_id))
    session = AgentSession(
        id=agent_id,
        workspace=workspace,
        phase=AgentPhase.CREATED,
        prompt=prompt,
        created_at=now,
        updated_at=now,
        log_path=log,
    )
    save_session(app, session)
    return session


def save_session(app: Application, session: AgentSession) -> None:
    storage = _storage_dir(app)
    session.updated_at = datetime.now(UTC).isoformat()
    _session_path(storage, session.id).write_text(json.dumps(session.to_dict(), indent=2))


def load_session(app: Application, agent_id: str) -> AgentSession:
    storage = _storage_dir(app)
    path = _session_path(storage, agent_id)
    if not path.is_file():
        app.abort(f"No agent session found with id: {agent_id}")
    data = json.loads(path.read_text())
    return msgspec.convert(data, AgentSession)


def load_all_sessions(app: Application) -> list[AgentSession]:
    storage = _storage_dir(app)
    sessions = []
    for p in sorted(storage.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            sessions.append(msgspec.convert(data, AgentSession))
        except Exception:  # noqa: BLE001
            continue
    return sorted(sessions, key=lambda s: s.created_at, reverse=True)


def find_active_session(app: Application) -> AgentSession | None:
    for session in load_all_sessions(app):
        if session.phase in ACTIVE_PHASES:
            return session
    return None
