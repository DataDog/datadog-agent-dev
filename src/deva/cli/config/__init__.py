# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from deva.cli.base import dynamic_group


@dynamic_group(
    short_help="Manage the config file",
    subcommands=(
        "explore",
        "find",
        "restore",
        "set",
        "show",
    ),
)
def cmd() -> None:
    pass
