# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.cli.env.dev.utils import option_env_type

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Check the status of a developer environment")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@pass_app
def cmd(app: Application, *, env_type: str, instance: str) -> None:
    """
    Check the status of a developer environment.
    """
    from dda.env.dev import get_dev_env

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    status = env.status()
    app.display(f"State: {status.state.value}")
    if status.info:
        app.display(status.info)
