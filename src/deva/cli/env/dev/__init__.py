# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from deva.cli.base import dynamic_group


@dynamic_group(
    short_help="Work with developer environments",
    subcommands=(
        "code",
        "gui",
        "ls",
        "remove",
        "run",
        "shell",
        "start",
        "status",
        "stop",
    ),
)
def cmd() -> None:
    pass
