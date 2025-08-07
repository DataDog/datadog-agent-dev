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
    "files",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    nargs=-1,
)
@click.option(
    "--owners-file",
    "owners_file",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to CODEOWNERS file",
    default=".github/CODEOWNERS",
)
def cmd(files: tuple[str, ...], *, owners_file: str) -> None:
    """
    Gets the code owners for the specified files.
    """
    import codeowners

    with open(owners_file, "r") as f:
        owners = codeowners.CodeOwners(f.read())

    res = {file: [owner[1] for owner in owners.of(file)] for file in files}

    print(res)
