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


@dynamic_command(
    short_help="Run a command within a developer environment",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", required=True, nargs=-1)
@option_env_type()
@click.pass_context
def cmd(ctx: click.Context, args: tuple[str, ...], env_type: str) -> None:
    """
    Run a command within a developer environment.
    """
    app: Application = ctx.obj
    first_arg = args[0]
    if first_arg in {"-h", "--help"}:
        app.display(ctx.get_help())
        app.abort(code=0)

    from deva.env.dev import get_dev_env

    env = get_dev_env(env_type)(
        app=app,
        name=env_type,
    )
    # Elide a status check and attempt run the command directly in order to improve responsiveness
    env.run_command(list(args))
