# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from unittest.mock import ANY, patch


class TestSelfFeatureEnabled:
    def test_prints_true(self, dda):
        with patch("dda.feature_flags.manager.FeatureFlagManager.enabled", return_value=True) as mocked_enabled:
            result = dda("self", "feature", "enabled", "my-flag")

        result.check(exit_code=0, stdout="true\n")
        # Called with (self, flag) and kwargs
        print(mocked_enabled.call_args.args)
        args, kwargs = mocked_enabled.call_args
        assert args[0] == "my-flag"
        assert kwargs == {"default": False, "scopes": None}

    def test_prints_false_and_passes_scopes_and_default(self, dda):
        with patch("dda.feature_flags.manager.FeatureFlagManager.enabled", return_value=False) as mocked_enabled:
            result = dda(
                "self",
                "feature",
                "enabled",
                "another-flag",
                "--default",
                "true",
                "--scope",
                "env=ci",
                "--scope",
                "team=agent",
            )

        result.check(exit_code=0, stdout="false\n")
        args, kwargs = mocked_enabled.call_args
        assert args[0] == "another-flag"
        assert kwargs == {"default": True, "scopes": {"env": "ci", "team": "agent"}}

    def test_invalid_scope_fails(self, dda, helpers):
        result = dda("self", "feature", "enabled", "flag", "--scope", "invalid")
        result.check_exit_code(2)
        helpers.assert_output_match(
            result.output,
            """expected key=value""",
            exact=False,
        )


