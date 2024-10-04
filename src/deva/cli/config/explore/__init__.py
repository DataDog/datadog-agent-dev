# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(short_help="Open the config location in your file manager")
@click.pass_obj
def cmd(app: Application) -> None:
    """Open the config location in your file manager."""
    click.launch(str(app.config_file.path), locate=True)
