# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os

import pytest


def test_standard(dda, config_file, helpers):
    config_file.data["terminal"]["verbosity"] = 2
    config_file.save()

    result = dda("config", "restore")

    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            Settings were successfully restored.
            """
        ),
    )

    config_file.restore()
    assert config_file.data["terminal"]["verbosity"] == 0


@pytest.mark.requires_unix
def test_restore_permissions(dda, config_file, helpers):
    config_file.path.unlink()

    old_umask = os.umask(0o002)
    try:
        result = dda("config", "restore")
    finally:
        os.umask(old_umask)

    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            Settings were successfully restored.
            """
        ),
    )
    assert config_file.path.stat().st_mode & 0o777 == 0o664


def test_allow_invalid_config(dda, config_file, helpers):
    config_file.data["terminal"]["verbosity"] = "foo"
    config_file.save()

    result = dda("config", "restore")

    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            Settings were successfully restored.
            """
        ),
    )
