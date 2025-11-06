# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command
from dda.cli.env.qa.utils import option_env_type

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="Run a command within a QA environment",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", required=True, nargs=-1)
@option_env_type()
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.pass_context
def cmd(ctx: click.Context, *, args: tuple[str, ...], env_type: str, instance: str) -> None:
    """
    Run a command within a QA environment.
    """
    app: Application = ctx.obj
    first_arg = args[0]
    if first_arg in {"-h", "--help"}:
        app.display(ctx.get_help())
        app.abort(code=0)

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
            f"QA environment `{instance}` of type `{env_type}` is in state `{status.state}`, must be `{expected_state}`"
        )

    env.run_command(list(args))
