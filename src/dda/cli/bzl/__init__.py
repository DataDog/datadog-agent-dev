# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, get_raw_args

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="Run Bazel commands",
    context_settings={"help_option_names": [], "ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
def cmd(ctx: click.Context) -> None:
    app: Application = ctx.obj
    with app.tools.bazel.ignore_arg_limits():
        process = app.tools.bazel.attach(get_raw_args(ctx), check=False)

    app.abort(code=process.returncode)
