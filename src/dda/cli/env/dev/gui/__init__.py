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


@dynamic_command(short_help="Access a developer environment through a graphical interface")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.pass_obj
def cmd(app: Application, *, env_type: str, instance: str) -> None:
    """
    Access a developer environment through a graphical interface.
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
        app.abort(f"Developer environment `{env_type}` is in state `{status.state}`, must be `{expected_state}`")

    try:
        env.launch_gui()
    except NotImplementedError:
        app.abort(f"Developer environment type does not support GUI access: {env_type}")
