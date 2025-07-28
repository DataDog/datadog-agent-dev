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


@dynamic_command(short_help="Open the Agent config location in your file manager")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@pass_app
def cmd(app: Application, *, env_type: str, instance: str) -> None:
    """
    Open the Agent config location in your file manager.
    """
    from dda.env.qa import get_qa_env

    env = get_qa_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    if not env.agent_config_dir.is_dir():
        app.abort(f"QA environment `{instance}` of type `{env_type}` does not exist")

    click.launch(str(env.agent_config.path), locate=True)
