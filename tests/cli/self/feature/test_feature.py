# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import shlex
import subprocess
import sys

import pytest

from dda.config.constants import AppEnvVars
from dda.feature_flags.manager import LEGACY_CI_TOKEN_ENV_VARS, CIFeatureFlagManager, FeatureFlagEvaluationResult


def python_command(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def command_string(args: list[str]) -> str:
    return subprocess.list2cmdline(args) if sys.platform == "win32" else shlex.join(args)


@pytest.fixture
def ci_manager(app, monkeypatch, mocker):
    for var in (
        AppEnvVars.FEATURE_FLAGS_CLIENT_TOKEN,
        AppEnvVars.FEATURE_FLAGS_CI_TOKEN_COMMAND,
        *LEGACY_CI_TOKEN_ENV_VARS,
    ):
        monkeypatch.delenv(var, raising=False)
    mocker.patch.object(app, "display_warning")
    return CIFeatureFlagManager(app)


@pytest.fixture
def set_token_command(config_file):
    def set_command(command: list[str]) -> None:
        config_file.data["feature-flags"] = {"ci": {"token-command": command}}
        config_file.save()

    return set_command


@pytest.fixture
def legacy_linux_vars(monkeypatch, mocker):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(AppEnvVars.FEATURE_FLAGS_CI_VAULT_PATH, "path")
    monkeypatch.setenv(AppEnvVars.FEATURE_FLAGS_CI_VAULT_KEY, "key")
    return mocker.patch("dda.feature_flags.manager.fetch_secret_ci", return_value="from-legacy")


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

    def test_token_env_var_bypasses_command(self, ci_manager, set_token_command, monkeypatch, mocker):
        set_token_command(python_command("print('from-command')"))
        monkeypatch.setenv(AppEnvVars.FEATURE_FLAGS_CLIENT_TOKEN, "from-env")
        run = mocker.patch("subprocess.run")

        assert ci_manager._get_client_token() == "from-env"  # noqa: SLF001
        run.assert_not_called()

    def test_empty_token_env_var_ignored(self, ci_manager, set_token_command, monkeypatch):
        set_token_command(python_command("print('from-command')"))
        monkeypatch.setenv(AppEnvVars.FEATURE_FLAGS_CLIENT_TOKEN, "")

        assert ci_manager._get_client_token() == "from-command"  # noqa: SLF001

    @pytest.mark.parametrize(
        ("env_command", "expected"),
        [
            pytest.param(None, "from-config", id="config"),
            pytest.param(command_string(python_command("print('from-env')")), "from-env", id="env overrides config"),
            pytest.param("", "from-config", id="empty env ignored"),
            pytest.param("  ", "from-config", id="blank env ignored"),
        ],
    )
    def test_token_command_env_var(self, ci_manager, set_token_command, monkeypatch, env_command, expected):
        set_token_command(python_command("print('from-config')"))
        if env_command is not None:
            monkeypatch.setenv(AppEnvVars.FEATURE_FLAGS_CI_TOKEN_COMMAND, env_command)

        assert ci_manager._get_client_token() == expected  # noqa: SLF001

    def test_token_command_output_stripped(self, ci_manager, set_token_command):
        set_token_command(
            python_command("import sys; print('noise', file=sys.stderr); sys.stdout.write('  tok\\r\\n')")
        )

        assert ci_manager._get_client_token() == "tok"  # noqa: SLF001

    def test_token_command_executable_resolved_on_windows(self, ci_manager, set_token_command, monkeypatch, mocker):
        monkeypatch.setattr("dda.utils.process.PLATFORM_ID", "windows")
        which = mocker.patch("shutil.which", return_value=sys.executable)
        set_token_command(["python-shim", "-c", "print('tok')"])

        assert ci_manager._get_client_token() == "tok"  # noqa: SLF001
        which.assert_called_once_with("python-shim")

    @pytest.mark.parametrize(
        ("command", "error", "timeout"),
        [
            pytest.param(
                python_command("import sys; print('boom', file=sys.stderr); sys.exit(3)"),
                "exited with code 3: boom",
                30,
                id="non-zero exit",
            ),
            pytest.param(python_command("print('  ')"), "returned no output", 30, id="empty output"),
            pytest.param(["dda-test-nonexistent-command"], "dda-test-nonexistent-command", 30, id="missing executable"),
            pytest.param(python_command("import time; time.sleep(10)"), "timed out", 0.5, id="timeout"),
        ],
    )
    def test_token_command_failure_defaults_flag(
        self, ci_manager, set_token_command, app, mocker, command, error, timeout
    ):
        mocker.patch("dda.feature_flags.manager.TOKEN_COMMAND_TIMEOUT", timeout)
        set_token_command(command)

        result = ci_manager.enabled("my-flag", default=True)

        assert result.value is True
        assert result.defaulted is True
        assert error in result.error
        app.display_warning.assert_called_once()

    def test_token_command_takes_precedence_over_legacy(self, ci_manager, set_token_command, app, legacy_linux_vars):
        set_token_command(python_command("print('from-command')"))

        assert ci_manager._get_client_token() == "from-command"  # noqa: SLF001
        legacy_linux_vars.assert_not_called()
        app.display_warning.assert_not_called()

    def test_legacy_fallback_is_deprecated(self, ci_manager, app, legacy_linux_vars):
        assert ci_manager._get_client_token() == "from-legacy"  # noqa: SLF001
        legacy_linux_vars.assert_called_once_with("path", "key")
        app.display_warning.assert_called_once()
        assert "deprecated" in app.display_warning.call_args.args[0]

    def test_nothing_configured(self, ci_manager, app):
        assert ci_manager._get_client_token() is None  # noqa: SLF001
        app.display_warning.assert_not_called()


class TestCITokenCommandEnvVar:
    def test_string_command_from_env(self, dda, monkeypatch, mocker):
        command = command_string(python_command("print('from-env-command')"))
        monkeypatch.setenv("CI", "true")
        monkeypatch.delenv(AppEnvVars.FEATURE_FLAGS_CLIENT_TOKEN, raising=False)
        monkeypatch.setenv(AppEnvVars.FEATURE_FLAGS_CI_TOKEN_COMMAND, command)
        client = mocker.patch("dda.feature_flags.manager.DatadogFeatureFlag")
        client.return_value.get_flag_value.return_value = True

        result = dda("self", "feature", "my-flag")

        result.check(exit_code=0, stdout="True\n")
        assert client.call_args.args[0] == "from-env-command"
