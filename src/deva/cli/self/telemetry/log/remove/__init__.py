# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(short_help="Clear the log")
@click.pass_obj
def cmd(app: Application) -> None:
    """
    Clear the log.
    """
    app.display(app.telemetry.read_log())
