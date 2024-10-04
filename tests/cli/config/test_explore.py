# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def test(deva, config_file, mocker):
    mock = mocker.patch("click.launch")
    result = deva("config", "explore")

    assert result.exit_code == 0, result.output
    mock.assert_called_once_with(str(config_file.path), locate=True)
