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


@dynamic_command(short_help="Show the cache size")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@pass_app
def cmd(app: Application, *, env_type: str, instance: str) -> None:
    """
    Show the cache size.
    """
    from binary import convert_units

    from dda.env.dev import get_dev_env

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    size = env.cache_size()

    value, unit = convert_units(size, exact=True)
    if not value:
        app.display("Empty")
    elif unit == "B":
        app.display(f"{value} {unit}")
    else:
        app.display(f"{value:.2f} {unit}")
