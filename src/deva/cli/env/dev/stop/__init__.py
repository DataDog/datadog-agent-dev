# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command
from deva.cli.env.dev.utils import option_env_type

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(short_help="Stop a developer environment")
@option_env_type()
@click.pass_obj
def cmd(app: Application, env_type: str) -> None:
    """
    Stop a developer environment.
    """
    from deva.env.dev import get_dev_env
    from deva.env.models import EnvironmentStage

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
    )
    status = env.status()
    expected_stage = EnvironmentStage.ACTIVE
    if status.stage != expected_stage:
        app.abort(
            f"Cannot stop developer environment `{env_type}` in stage `{status.stage}`, must be `{expected_stage}`"
        )

    env.remove_config()
