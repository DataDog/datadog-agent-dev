# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def test(dda, helpers, machine_id):
    result = dda("self", "telemetry", "show", "id")
    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            {machine_id}
            """
        ),
    )
