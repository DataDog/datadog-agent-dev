# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import click

from dda.cli.base import dynamic_command
from dda.utils.fs import Path


@dynamic_command(short_help="""Internal command used to call import_from_dir in dev envs.""", hidden=True)
@click.argument(
    "source", required=True, type=click.Path(exists=True, resolve_path=True, file_okay=False, path_type=Path)
)
@click.argument("destination", required=True, type=click.Path(resolve_path=True, path_type=Path))
# Use arguments instead of options to enforce the idea that these are required
@click.argument("recursive", required=True, type=bool)
@click.argument("force", required=True, type=bool)
@click.argument("mkpath", required=True, type=bool)
def cmd(
    *,
    source: Path,
    destination: Path,
    recursive: bool,
    force: bool,
    mkpath: bool,
) -> None:
    """
    Internal command used to call import_from_dir in dev envs.
    This allows us to use the same semantics for importing files and directories into a dev env as for exporting them on the host filesystem.
    """
    from dda.env.dev.fs import import_from_dir

    import_from_dir(source, destination, recursive=recursive, force=force, mkpath=mkpath)
