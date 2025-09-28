# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def test(dda, config_file, helpers):
    result = dda("config", "find")

    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            {config_file.path}
            """
        ),
    )
