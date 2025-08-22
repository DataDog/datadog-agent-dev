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
    "--owners",
    "-f",
    "owners_filepath",
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
def cmd(app: Application, paths: tuple[Path, ...], *, owners_filepath: Path, json: bool) -> None:
    """
    Gets the code owners for the specified paths.
    """
    import codeowners

    owners = codeowners.CodeOwners(owners_filepath.read_text(encoding="utf-8"))

    # The codeowners library expects paths to be in POSIX format (even on Windows)
    res = {(posix_path := path.as_posix()): [owner[1] for owner in owners.of(posix_path)] for path in paths}
    if json:
        from json import dumps

        app.output(dumps(res))
    else:
        # Note: paths here are in POSIX format, so they will use / even on Windows
        display_res = {path: ", ".join(owners) for path, owners in res.items()}
        app.display_table(display_res, stderr=False)
