# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="Run Bazel commands",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", nargs=-1)
@pass_app
def cmd(app: Application, *, args: tuple[str, ...]) -> None:
    with app.tools.bazel.ignore_arg_limits():
        process = app.tools.bazel.attach(list(args), check=False)

    app.abort(code=process.returncode)
