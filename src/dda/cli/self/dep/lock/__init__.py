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
    short_help="Lock dependencies",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", nargs=-1)
@pass_app
def cmd(app: Application, *, args: tuple[str, ...]) -> None:
    """
    Lock dependencies.
    """
    import sys

    app.tools.uv.exit_with(["lock", "--python", sys.executable, *args])
