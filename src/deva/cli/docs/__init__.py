# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from deva.cli.base import dynamic_group


@dynamic_group(
    short_help="Manage documentation",
    subcommands=(
        "build",
        "serve",
    ),
)
def cmd() -> None:
    pass
