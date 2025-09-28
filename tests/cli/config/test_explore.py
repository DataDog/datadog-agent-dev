# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def test(dda, config_file, mocker):
    mock = mocker.patch("click.launch")
    result = dda("config", "explore")

    result.check(exit_code=0)
    mock.assert_called_once_with(str(config_file.path), locate=True)
