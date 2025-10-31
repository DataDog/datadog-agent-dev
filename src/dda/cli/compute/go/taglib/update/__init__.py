# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.build.go.tags import DEFAULT_TAG_LIBRARY_FILE
from dda.cli.base import dynamic_command

if TYPE_CHECKING:
    from dda.utils.fs import Path


@dynamic_command(
    short_help="Update the Go build tag library with the tags found in the repository.",
)
@click.option(
    "repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    help="The repository to use.",
)
@click.option(
    "library_file",
    "-l",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, resolve_path=True),
    default=DEFAULT_TAG_LIBRARY_FILE,
    help="The path to the library file to update.",
)
def cmd(repo: Path, *, library_file: Path) -> None:
    pass
