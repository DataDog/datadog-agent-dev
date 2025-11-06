# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Show the active QA environments")
@pass_app
def cmd(app: Application) -> None:
    """
    Show the active QA environments.
    """
    import json

    from dda.env.qa import get_qa_env

    env_data = {}
    storage_dirs = app.config.storage.join("env", "qa")
    if not storage_dirs.data.is_dir():
        app.display("No QA environments found")
        return

    for env_type in sorted(storage_dirs.data.iterdir()):
        type_name = env_type.name
        instance_data = {}
        for instance in sorted(env_type.iterdir()):
            instance_name = instance.name
            env = get_qa_env(type_name)(
                app=app,
                name=type_name,
                instance=instance_name,
            )
            if env.config_file.is_file():
                env_status = env.status()
                config = {
                    key: value
                    for key, value in json.loads(env.config_file.read_text()).items()
                    # Filter out `None` and empty containers
                    if value or value is False
                }
                instance_data[instance_name] = {
                    "State": env_status.state,
                    "Config": config,
                }

        if instance_data:
            env_data[type_name] = instance_data

    if not env_data:
        app.display("No QA environments found")
        return

    app.display_table(env_data)
