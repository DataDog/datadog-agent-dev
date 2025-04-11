# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Open the config location in your file manager")
@pass_app
def cmd(app: Application) -> None:
    """Open the config location in your file manager."""
    click.launch(str(app.config_file.path), locate=True)
