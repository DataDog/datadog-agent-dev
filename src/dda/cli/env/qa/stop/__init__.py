# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.cli.env.qa.utils import option_env_type

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Stop a QA environment")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.option("-r", "--remove", is_flag=True, help="Remove the environment after stopping")
@pass_app
def cmd(app: Application, *, env_type: str, instance: str, remove: bool) -> None:
    """
    Stop a QA environment.
    """
    from dda.env.models import EnvironmentState
    from dda.env.qa import get_qa_env

    env = get_qa_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    status = env.status()
    expected_state = EnvironmentState.STARTED
    if status.state != expected_state:
        app.abort(
            f"Cannot stop QA environment `{instance}` of type `{env_type}` in state `{status.state}`, "
            f"must be `{expected_state}`"
        )

    env.stop()
    if remove:
        env.remove()
        env.remove_state()
