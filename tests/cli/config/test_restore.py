# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def test_standard(dda, config_file):
    config_file.data["terminal"]["verbosity"] = 2
    config_file.save()

    result = dda("config", "restore")

    assert result.exit_code == 0, result.output
    assert result.output == "Settings were successfully restored.\n"

    config_file.restore()
    assert config_file.data["terminal"]["verbosity"] == 0


def test_allow_invalid_config(dda, config_file, helpers):
    config_file.data["terminal"]["verbosity"] = "foo"
    config_file.save()

    result = dda("config", "restore")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Settings were successfully restored.
        """
    )
