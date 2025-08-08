# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.utils.fs import Path

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Find code owners of files and directories", features=["codeowners"])
@click.argument(
    "paths",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    nargs=-1,
)
@click.option(
    "--config",
    "-c",
    "config_filepath",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to CODEOWNERS file",
    default=".github/CODEOWNERS",
)
# TODO: Make this respect any --non-interactive flag or other way to detect CI environment
@click.option(
    "--json",
    is_flag=True,
    help="Format the output as JSON",
)
@pass_app
def cmd(app: Application, paths: tuple[Path, ...], *, config_filepath: Path, json: bool) -> None:
    """
    Gets the code owners for the specified paths.
    """
    import codeowners

    with config_filepath.open(encoding="utf-8") as f:
        owners = codeowners.CodeOwners(f.read())

    res = {str(path): [owner[1] for owner in owners.of(str(path))] for path in paths}

    if json:
        from json import dumps

        app.output(dumps(res))
    else:
        display_res = {path: ", ".join(owners) for path, owners in res.items()}
        app.display_table(display_res)
