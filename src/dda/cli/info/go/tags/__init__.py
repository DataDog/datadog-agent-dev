# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command

if TYPE_CHECKING:
    from dda.utils.fs import Path


@dynamic_command(
    short_help="Query the list of Go build tags existing in the repository.",
)
@click.option(
    "repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    help="The repository to use.",
)
@click.option("--json", "-j", is_flag=True, help="Format the output as JSON.")
def cmd(repo: Path, *, json: bool) -> None:
    pass
