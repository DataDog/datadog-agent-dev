# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.cli.env.dev.utils import option_env_type

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Remove the cache")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@pass_app
def cmd(app: Application, *, env_type: str, instance: str) -> None:
    """
    Remove the cache.
    """
    from dda.env.dev import get_dev_env
    from dda.env.models import EnvironmentState

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    status = env.status()
    transition_states = {EnvironmentState.NONEXISTENT, EnvironmentState.STOPPED}
    if status.state not in transition_states:
        app.abort(
            f"Cannot remove cache for developer environment `{env_type}` in state `{status.state}`, must be one of: "
            f"{', '.join(sorted(transition_states))}"
        )

    env.remove_cache()
