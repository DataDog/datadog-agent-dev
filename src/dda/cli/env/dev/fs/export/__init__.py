# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.cli.env.dev.utils import option_env_type
from dda.utils.fs import Path

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="""Export files and directories from a developer environment""",
)
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.argument("source", required=True)
@click.argument(
    "destination",
    required=True,
    type=click.Path(file_okay=True, dir_okay=True, writable=True, resolve_path=True, path_type=Path),
)
@pass_app
def cmd(
    app: Application,
    *,
    env_type: str,
    instance: str,
    source: str,  # Passed as string since it is inside the env filesystem
    destination: Path,
) -> None:
    """
    Export files and directories from a developer environment, using an interface similar to `cp`.
    The last path specified is the destination directory on the host filesystem.

    Paths within the environment (source) need to be passed as _absolute paths_.
    Paths on the host filesystem (destination) can be relative or absolute.
    """
    from dda.env.dev import get_dev_env
    from dda.env.models import EnvironmentState

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    status = env.status()

    if status.state != EnvironmentState.STARTED:
        app.abort(
            f"Developer environment `{env_type}` is in state `{status.state}`, must be {EnvironmentState.STARTED}."
        )

    try:
        env.export_path(source, destination)
    except Exception as error:  # noqa: BLE001
        app.abort(f"Failed to export files: {error}")
