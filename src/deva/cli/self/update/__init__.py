# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(
    short_help="Install the latest version",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", nargs=-1)
@click.pass_obj
def cmd(app: Application, *, args: tuple[str, ...]) -> None:  # noqa: ARG001
    app.abort("deva is not installed as a binary")
