# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from deva.cli.base import dynamic_group


@dynamic_group(
    short_help="Manage telemetry submission",
    subcommands=(
        "disable",
        "enable",
        "log",
    ),
)
def cmd() -> None:
    pass
