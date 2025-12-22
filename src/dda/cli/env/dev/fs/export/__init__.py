# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command
from dda.cli.env.dev.utils import option_env_type
from dda.utils.fs import Path

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="""Export files and directories from a developer environment""",
)
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.argument("sources", nargs=-1, required=True, type=click.Path(exists=True, resolve_path=True, path_type=Path))
@click.argument("destination", required=True, type=click.Path(resolve_path=True, path_type=Path))
@click.option("--recursive", "-r", is_flag=True, help="Import files and directories recursively.")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing files. Without this option, an error will be raised if the destination file already exists.",
)
@click.option(
    "--mkpath", is_flag=True, help="Create the destination directories and their parents if they do not exist."
)
def cmd(
    app: Application,
    *,
    env_type: str,
    instance: str,
    sources: tuple[Path, ...],
    destination: Path,
    recursive: bool,
    force: bool,
    mkpath: bool,
) -> None:
    """
    Export files and directories from a developer environment, using an interface similar to `cp`.
    The last path specified is the destination directory on the host filesystem.
    """
    from dda.env.dev import get_dev_env
    from dda.env.models import EnvironmentState

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    status = env.status()

    # TODO: This might end up depending on the environment type.
    # For `linux-container` though, `docker cp` also works on stopped containers.
    possible_states = {EnvironmentState.STARTED, EnvironmentState.STOPPED}
    if status.state not in possible_states:
        app.abort(
            f"Developer environment `{env_type}` is in state `{status.state}`, must be one of: "
            f"{', '.join(sorted(possible_states))}"
        )

    try:
        env.export_files(sources, destination, recursive, force, mkpath)
    except Exception as error:  # noqa: BLE001
        app.abort(f"Failed to export files: {error}")
