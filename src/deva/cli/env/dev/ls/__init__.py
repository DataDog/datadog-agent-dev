# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(short_help="List the available developer environments")
@click.pass_obj
def cmd(app: Application) -> None:
    """
    List the available developer environments.
    """
    import json

    from deva.env.dev import get_dev_env

    env_data = {}
    storage_dirs = app.config.storage.join("env", "dev")
    for env_type in sorted(storage_dirs.data.iterdir()):
        type_name = env_type.name
        instance_data = {}
        for instance in sorted(env_type.iterdir()):
            instance_name = instance.name
            env = get_dev_env(type_name)(
                app=app,
                name=type_name,
                instance=instance_name,
            )
            if env.config_file.is_file():
                env_status = env.status()
                instance_data[instance_name] = {
                    "State": env_status.state,
                    "Config": json.loads(env.config_file.read_text()),
                }

        if instance_data:
            env_data[type_name] = instance_data

    if not env_data:
        app.display("No developer environments found")
        return

    app.display_table(env_data)
