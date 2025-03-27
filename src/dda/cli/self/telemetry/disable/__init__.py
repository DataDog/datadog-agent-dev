# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Disable telemetry")
@click.pass_obj
def cmd(app: Application) -> None:
    """
    Disable telemetry.
    """
    app.telemetry.dissent()
