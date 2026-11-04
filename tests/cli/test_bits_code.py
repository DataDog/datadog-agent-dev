# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import pytest

from dda.cli.application import UpdateChecker
from dda.telemetry.manager import TelemetryManager


@pytest.mark.parametrize("options", [[], ["--force"], ["--no-config"]])
def test_ddgl_setup_hands_off_before_tool_or_token_setup(dda, monkeypatch, mocker, options):
    monkeypatch.setenv("DD_BITS_CODE", "1")
    lookup = mocker.patch("dda.cli.tools.ddgl.setup.which", side_effect=AssertionError("tool lookup"))
    result = dda("tools", "ddgl", "setup", *options)
    result.check_exit_code(1)
    assert "authenticated host" in result.output
    lookup.assert_not_called()


def test_bits_lifecycle_skips_optional_auth_and_updates(dda, monkeypatch, mocker):
    monkeypatch.setenv("DD_BITS_CODE", "1")
    update = mocker.patch.object(UpdateChecker, "ready", side_effect=AssertionError("update check"))
    daemon = mocker.patch.object(
        TelemetryManager, "_TelemetryManager__start_daemon", side_effect=AssertionError("telemetry")
    )
    result = dda("config", "show")
    result.check_exit_code(0)
    update.assert_not_called()
    daemon.assert_not_called()


def test_bits_marker_does_not_enable_mode_for_other_values(monkeypatch):
    from dda.utils.bits import running_in_bits_code

    monkeypatch.setenv("DD_BITS_CODE", "0")
    assert not running_in_bits_code()


def test_bits_telemetry_does_not_discover_credentials(app, monkeypatch, mocker):
    monkeypatch.setenv("DD_BITS_CODE", "1")
    manager = TelemetryManager(app)
    # Isolate consent from the suite's on-disk telemetry opt-out.
    manager.__dict__["_TelemetryManager__dissent_file"] = mocker.Mock(is_file=lambda: False)
    read_key = mocker.patch("dda.secrets.api.read_api_key", side_effect=AssertionError("credential read"))
    fetch_key = mocker.patch("dda.secrets.api.fetch_api_key", side_effect=AssertionError("credential fetch"))
    assert not manager.enabled
    assert manager.api_key is None
    read_key.assert_not_called()
    fetch_key.assert_not_called()
