# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application
    from rich.text import Text


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
# TODO: Make this respect any --non-interactive flag or other way to detect CI environment
@click.option(
    "--pretty/--no-pretty",
    help="Format the output in a human-readable format instead of JSON object",
    default=True,
)
@pass_app
def cmd(
    app: Application, files: tuple[str, ...], *, owners_file: str, pretty: bool
) -> None:
    """
    Gets the code owners for the specified files.
    """
    import codeowners

    with open(owners_file, "r") as f:
        owners = codeowners.CodeOwners(f.read())

    res = {file: [owner[1] for owner in owners.of(file)] for file in files}

    if pretty:
        display_res = {file: ", ".join(owners) for file, owners in res.items()}
        app.display_table(display_res)
    else:
        from json import dumps

        app.output(dumps(res))
