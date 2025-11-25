# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.feature_flags.manager import CIFeatureFlagManager, FeatureFlagEvaluationResult


class TestSelfFeatureEnabled:
    def test_prints_true(self, dda, mocker):
        mocked_enabled = mocker.patch(
            "dda.feature_flags.manager.FeatureFlagManager.enabled",
            return_value=FeatureFlagEvaluationResult(value="true", defaulted=False, error=None),
        )
        result = dda("self", "feature", "my-flag")

        result.check(exit_code=0, stdout="true\n")
        # Called with (self, flag) and kwargs
        args, kwargs = mocked_enabled.call_args
        assert args[0] == "my-flag"
        assert kwargs == {"default": False, "scopes": None}

    def test_prints_false_and_passes_scopes_and_default(self, dda, mocker):
        mocked_enabled = mocker.patch(
            "dda.feature_flags.manager.FeatureFlagManager.enabled",
            return_value=FeatureFlagEvaluationResult(value="false", defaulted=True, error=None),
        )
        result = dda(
            "self",
            "feature",
            "another-flag",
            "--default",
            "true",
            "--scope",
            "env",
            "ci",
            "--scope",
            "team",
            "agent",
        )

        result.check(exit_code=0, stdout="false\n")
        args, kwargs = mocked_enabled.call_args
        assert args[0] == "another-flag"
        assert kwargs == {"default": True, "scopes": {"env": "ci", "team": "agent"}}

    def test_invalid_scope_fails(self, dda, helpers):
        result = dda("self", "feature", "flag", "--scope", "invalid")
        result.check_exit_code(2)
        helpers.assert_output_match(
            result.output,
            """requires 2 arguments""",
            exact=False,
        )

    def test_json_output(self, dda, mocker):
        mocked_enabled = mocker.patch(
            "dda.feature_flags.manager.FeatureFlagManager.enabled",
            return_value=FeatureFlagEvaluationResult(value="true", defaulted=True, error="Something random happened"),
        )
        result = dda("self", "feature", "my-flag", "--json")
        result.check(
            exit_code=0, stdout_json={"value": "true", "defaulted": True, "error": "Something random happened"}
        )
        args, kwargs = mocked_enabled.call_args
        assert args[0] == "my-flag"
        assert kwargs == {"default": False, "scopes": None}


class TestCIFeatureFlagManager:
    def test_get_author_from_ci(self):
        manager = CIFeatureFlagManager(None)

        assert manager.get_author_from_ci("John Doe <john.doe@example.com>") == "john.doe@example.com"
        assert manager.get_author_from_ci("<john.doe@example.com>") == "john.doe@example.com"
        assert manager.get_author_from_ci("John Doe") == ""
