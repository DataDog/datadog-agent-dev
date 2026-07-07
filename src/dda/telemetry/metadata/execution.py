# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os

from dda.utils.platform import PLATFORM_ID


def _enabled(name: str) -> bool:
    return os.environ.get(name) in {"1", "true"}


def running_in_dev_env() -> bool:
    """
    Returns:
        Whether the current process is running inside a managed developer environment.
    """
    # The Linux container is the only developer environment today and marks itself with `/.started`.
    return PLATFORM_ID == "linux" and os.path.isfile("/.started")


def detect_medium() -> str:
    """
    Returns:
        How the CLI was reached: `mcp`, `pre-commit`, or `direct`.
    """
    # The MCP server sets this per call, so it is the strongest signal of how the CLI was reached.
    if os.environ.get("PYCLI_MCP_TOOL_NAME"):
        return "mcp"
    if _enabled("PRE_COMMIT"):
        return "pre-commit"
    return "direct"


def _agent_actor(name: str, medium: str | None, extra: str) -> str:
    # Compose the harness identity as `<name>[-<medium>]` (e.g. `claude-cli`). Without a categorized
    # medium, fall back to the bare name, preserving any uncategorized data as `<name> (...)`.
    if medium:
        return f"{name}-{medium}"
    if extra:
        return f"{name} {extra}"
    return name


def _detect_claude_actor(product: str, version: str, extra: str) -> str:  # noqa: ARG001
    # Claude Code: claude-code/2.1.195 (sdk-cli)
    # Claude Desktop: claude-code/2.1.197 (claude-desktop, agent-sdk/0.3.197)
    medium: str | None = None
    if "sdk-cli" in extra:
        medium = "cli"
    elif "claude-desktop" in extra:
        medium = "desktop"

    return _agent_actor("claude", medium, extra)


def detect_actor(medium: str) -> str:
    """
    Returns:
        Who invoked the CLI, such as `human` or an AI agent harness like `claude` or `codex`.
    """
    # The agent's environment is invisible across the MCP server, so the only signal is the
    # client's `User-Agent`, which the server forwards from the per-request HTTP headers.
    if medium == "mcp":
        # A `User-Agent` looks like `<product>/<version> <extra>`, e.g. `claude-code/2.1.195 (sdk-cli)`.
        user_agent = os.environ.get("PYCLI_MCP_USER_AGENT", "")
        product, _, rest = user_agent.partition("/")
        version, _, extra = rest.partition(" ")
        extra = extra.strip()

        actor = None
        if product == "claude-code":
            actor = _detect_claude_actor(product, version, extra)

        return actor or user_agent or "unknown"

    # Every other medium inherits the caller's environment, where harnesses leave identifying markers.
    if entrypoint := os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return _agent_actor(
            "claude",
            "cli" if entrypoint == "cli" else "desktop" if entrypoint == "claude-desktop" else None,
            entrypoint,
        )

    # The originator names a specific Codex surface and coexists with the generic CODEX_CI marker in
    # hosted environments, so categorize it before falling back to that marker.
    if originator := os.environ.get("CODEX_INTERNAL_ORIGINATOR_OVERRIDE"):
        return _agent_actor(
            "codex",
            "desktop" if originator == "Codex Desktop" else "cloud" if originator == "codex_web_agent" else None,
            originator,
        )

    if _enabled("CODEX_CI"):
        return "codex"

    if _enabled("CURSOR_AGENT"):
        return "cursor"

    if _enabled("PI_CODING_AGENT"):
        return "pi"

    if _enabled("ANTIGRAVITY_AGENT"):
        return "antigravity"

    return "human"
