# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app, get_installed_dependencies

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Show all installed dependencies")
@pass_app
def cmd(app: Application) -> None:
    """
    Show all installed dependencies.

    Example:

    ```
    dda self dep show
    ```
    """
    click.echo(get_installed_dependencies(app=app))
