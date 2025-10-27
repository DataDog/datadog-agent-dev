# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command
from dda.cli.compute.go.taglib.constants import DEFAULT_TAG_LIBRARY_FILE

if TYPE_CHECKING:
    from dda.utils.fs import Path


@dynamic_command(
    short_help="Add a configuration to a Go build tag library.",
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
    help="The path to the library file to add the configuration to.",
)
def cmd(repo: Path, *, library_file: Path) -> None:
    pass
