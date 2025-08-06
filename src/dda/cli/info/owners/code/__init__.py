# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import click

from dda.cli.base import dynamic_command


@dynamic_command(
    short_help="Gets the code owners for the specified file.", features=["codeowners"]
)
@click.argument(
    "file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
)
@click.option(
    "--owners-file",
    "owners_file",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to CODEOWNERS file",
    default=".github/CODEOWNERS",
)
def cmd(file: str, *, owners_file: str) -> None:
    """
    Gets the code owners for the specified file.
    """
    import codeowners

    with open(owners_file, "r") as f:
        owners = codeowners.CodeOwners(f.read())
    owners_list = owners.of(file)

    print(", ".join(owner[1] for owner in owners_list))
