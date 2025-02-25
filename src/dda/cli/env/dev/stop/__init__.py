# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command
from dda.cli.env.dev.utils import option_env_type

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Stop a developer environment")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.option("-r", "--remove", is_flag=True, help="Remove the environment after stopping")
@click.pass_obj
def cmd(app: Application, *, env_type: str, instance: str, remove: bool) -> None:
    """
    Stop a developer environment.
    """
    from dda.env.dev import get_dev_env
    from dda.env.models import EnvironmentState

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    status = env.status()
    expected_state = EnvironmentState.STARTED
    if status.state != expected_state:
        app.abort(
            f"Cannot stop developer environment `{env_type}` in state `{status.state}`, must be `{expected_state}`"
        )

    env.stop()
    if remove:
        env.remove()
        env.remove_config()
