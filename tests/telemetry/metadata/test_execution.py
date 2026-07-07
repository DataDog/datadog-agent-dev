# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.telemetry.metadata import execution
from dda.utils.process import EnvVars

# `EnvVars(..., exclude=["*"])` replaces the entire process environment with only the given
# variables, so ambient markers (e.g. a `CLAUDE_CODE_ENTRYPOINT` set by whatever launched the
# test suite) cannot leak into the detection logic under test.


class TestDetectMedium:
    def test_mcp(self):
        with EnvVars({"PYCLI_MCP_TOOL_NAME": "dda.self.version"}, exclude=["*"]):
            assert execution.detect_medium() == "mcp"

    def test_mcp_takes_precedence_over_pre_commit(self):
        with EnvVars({"PYCLI_MCP_TOOL_NAME": "dda.self.version", "PRE_COMMIT": "1"}, exclude=["*"]):
            assert execution.detect_medium() == "mcp"

    @pytest.mark.parametrize("value", ["1", "true"])
    def test_pre_commit(self, value):
        with EnvVars({"PRE_COMMIT": value}, exclude=["*"]):
            assert execution.detect_medium() == "pre-commit"

    def test_pre_commit_requires_enabled_value(self):
        with EnvVars({"PRE_COMMIT": "0"}, exclude=["*"]):
            assert execution.detect_medium() == "direct"

    def test_direct(self):
        with EnvVars({}, exclude=["*"]):
            assert execution.detect_medium() == "direct"


class TestDetectActorOverMcp:
    @pytest.mark.parametrize(
        ("user_agent", "expected"),
        [
            # Categorized Claude surfaces via the `User-Agent` comment.
            ("claude-code/2.1.195 (sdk-cli)", "claude-cli"),
            ("claude-code/2.1.197 (claude-desktop, agent-sdk/0.3.197)", "claude-desktop"),
            # Recognized product, but an uncategorized comment is preserved verbatim.
            ("claude-code/2.1.197 (native)", "claude (native)"),
            # Recognized product with no comment collapses to the bare name.
            ("claude-code/2.1.195", "claude"),
            # Unrecognized products fall back to the raw `User-Agent`.
            ("codex-cli/1.0.0 (foo)", "codex-cli/1.0.0 (foo)"),
            ("node", "node"),
        ],
    )
    def test_user_agent(self, user_agent, expected):
        with EnvVars({"PYCLI_MCP_USER_AGENT": user_agent}, exclude=["*"]):
            assert execution.detect_actor("mcp") == expected

    def test_empty_user_agent(self):
        with EnvVars({"PYCLI_MCP_USER_AGENT": ""}, exclude=["*"]):
            assert execution.detect_actor("mcp") == "unknown"

    def test_missing_user_agent(self):
        with EnvVars({}, exclude=["*"]):
            assert execution.detect_actor("mcp") == "unknown"

    def test_ignores_environment_markers(self):
        # Over MCP the agent's own environment is invisible, so local markers must not be consulted.
        with EnvVars({"PYCLI_MCP_USER_AGENT": "", "CLAUDE_CODE_ENTRYPOINT": "cli", "CODEX_CI": "1"}, exclude=["*"]):
            assert execution.detect_actor("mcp") == "unknown"


class TestDetectActorFromEnvironment:
    @pytest.mark.parametrize("medium", ["direct", "pre-commit"])
    def test_non_mcp_media_use_environment(self, medium):
        with EnvVars({"CODEX_CI": "1"}, exclude=["*"]):
            assert execution.detect_actor(medium) == "codex"

    @pytest.mark.parametrize(
        ("entrypoint", "expected"),
        [
            ("cli", "claude-cli"),
            ("claude-desktop", "claude-desktop"),
            ("vscode", "claude vscode"),
        ],
    )
    def test_claude_entrypoint(self, entrypoint, expected):
        with EnvVars({"CLAUDE_CODE_ENTRYPOINT": entrypoint}, exclude=["*"]):
            assert execution.detect_actor("direct") == expected

    def test_claude_entrypoint_takes_precedence(self):
        with EnvVars({"CLAUDE_CODE_ENTRYPOINT": "cli", "CODEX_CI": "1", "CURSOR_AGENT": "1"}, exclude=["*"]):
            assert execution.detect_actor("direct") == "claude-cli"

    @pytest.mark.parametrize(
        ("originator", "expected"),
        [
            ("Codex Desktop", "codex-desktop"),
            ("codex_web_agent", "codex-cloud"),
            # Uncategorized originators are preserved verbatim.
            ("codex_vscode", "codex codex_vscode"),
        ],
    )
    def test_codex_originator(self, originator, expected):
        with EnvVars({"CODEX_INTERNAL_ORIGINATOR_OVERRIDE": originator}, exclude=["*"]):
            assert execution.detect_actor("direct") == expected

    def test_codex_originator_takes_precedence_over_ci_marker(self):
        # Hosted Codex sets both; the specific surface must win over the generic CI marker.
        with EnvVars({"CODEX_INTERNAL_ORIGINATOR_OVERRIDE": "codex_web_agent", "CODEX_CI": "1"}, exclude=["*"]):
            assert execution.detect_actor("direct") == "codex-cloud"

    @pytest.mark.parametrize(
        ("variable", "expected"),
        [
            ("CODEX_CI", "codex"),
            ("CURSOR_AGENT", "cursor"),
            ("PI_CODING_AGENT", "pi"),
            ("ANTIGRAVITY_AGENT", "antigravity"),
        ],
    )
    @pytest.mark.parametrize("value", ["1", "true"])
    def test_boolean_markers(self, variable, value, expected):
        with EnvVars({variable: value}, exclude=["*"]):
            assert execution.detect_actor("direct") == expected

    @pytest.mark.parametrize("variable", ["CODEX_CI", "CURSOR_AGENT", "PI_CODING_AGENT", "ANTIGRAVITY_AGENT"])
    def test_boolean_markers_require_enabled_value(self, variable):
        # Anything other than `1`/`true` does not count as set.
        with EnvVars({variable: "0"}, exclude=["*"]):
            assert execution.detect_actor("direct") == "human"

    def test_marker_precedence(self):
        # `CODEX_CI` is checked before the other boolean markers.
        markers = {"CODEX_CI": "1", "CURSOR_AGENT": "1", "PI_CODING_AGENT": "1", "ANTIGRAVITY_AGENT": "1"}
        with EnvVars(markers, exclude=["*"]):
            assert execution.detect_actor("direct") == "codex"

    def test_human(self):
        with EnvVars({}, exclude=["*"]):
            assert execution.detect_actor("direct") == "human"


class TestRunningInDevEnv:
    def test_linux_with_marker(self, mocker):
        mocker.patch.object(execution, "PLATFORM_ID", "linux")
        mocker.patch("os.path.isfile", return_value=True)
        assert execution.running_in_dev_env() is True

    def test_linux_without_marker(self, mocker):
        mocker.patch.object(execution, "PLATFORM_ID", "linux")
        mocker.patch("os.path.isfile", return_value=False)
        assert execution.running_in_dev_env() is False

    @pytest.mark.parametrize("platform_id", ["windows", "macos"])
    def test_non_linux(self, mocker, platform_id):
        mocker.patch.object(execution, "PLATFORM_ID", platform_id)
        # The marker is present, so a `True` result would mean the platform gate was skipped.
        mocker.patch("os.path.isfile", return_value=True)
        assert execution.running_in_dev_env() is False
