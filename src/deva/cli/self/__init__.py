# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os

from deva.cli.base import dynamic_group

__subcommands = [
    "dep",
]

# We want the auto-generated documentation to include the default management commands:
# https://ofek.dev/pyapp/latest/runtime/#default
if os.environ.get("DEVA_DOCS_BUILD") == "1":
    __subcommands.extend((
        "remove",
        "restore",
        "update",
    ))


@dynamic_group(
    short_help="Manage deva",
    subcommands=tuple(sorted(__subcommands)),
)
def cmd() -> None:
    pass
