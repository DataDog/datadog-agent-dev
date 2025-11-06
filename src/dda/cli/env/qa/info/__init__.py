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


@dynamic_command(short_help="Show the metadata of a QA environment")
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.option("--status", "-s", "show_status", is_flag=True, help="Include the status of the environment")
@click.option("--json", "as_json", is_flag=True, help="Output the metadata as JSON")
@pass_app
def cmd(app: Application, *, env_type: str, instance: str, as_json: bool, show_status: bool) -> None:
    """
    Show the metadata of a QA environment.
    """
    import msgspec

    from dda.env.models import EnvironmentState
    from dda.env.qa import get_qa_env

    env = get_qa_env(env_type)(
        app=app,
        name=env_type,
        instance=instance,
    )
    status = env.status()
    if status.state == EnvironmentState.NONEXISTENT:
        app.abort(f"QA environment `{instance}` of type `{env_type}` does not exist")

    metadata = env.metadata()
    info = msgspec.to_builtins(metadata)
    if show_status:
        info["status"] = msgspec.to_builtins(status)

    info = dict(sorted(info.items()))
    if as_json:
        app.display(msgspec.json.encode(info).decode())
    else:
        app.display_table(info)
