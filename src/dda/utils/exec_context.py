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


def detect_actor(medium: str) -> str:
    """
    Returns:
        Who invoked the CLI, such as `human` or an AI agent harness like `claude` or `codex`.
    """
    # The agent's environment is invisible across the MCP server, so the only signal is the
    # client-defined identity that the server forwards from the connection handshake.
    if medium == "mcp":
        client = os.environ.get("PYCLI_MCP_CLIENT_NAME", "")
        if client == "claude-code":
            return "claude"

        if client == "claude-ai":
            return "claude-desktop"

        # Codex clients cannot be distinguished since they all report the same name.
        if client == "codex-mcp-client":
            return "codex"

        if client.startswith("cursor-vscode"):
            return "cursor"

        if client in {"agy", "antigravity-cli", "antigravity-client"}:
            return "antigravity"

        return client or "unknown"

    # Every other medium inherits the caller's environment, where harnesses leave identifying markers.
    if entrypoint := os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude-desktop" if entrypoint == "claude-desktop" else "claude"

    # This is only set in non-CLI contexts, so check it before the general marker.
    if os.environ.get("CODEX_INTERNAL_ORIGINATOR_OVERRIDE") == "Codex Desktop":
        return "codex-desktop"

    if _enabled("CODEX_CI"):
        return "codex"

    if _enabled("CURSOR_AGENT"):
        return "cursor"

    if _enabled("PI_CODING_AGENT"):
        return "pi"

    if _enabled("ANTIGRAVITY_AGENT"):
        return "antigravity"

    return "human"
