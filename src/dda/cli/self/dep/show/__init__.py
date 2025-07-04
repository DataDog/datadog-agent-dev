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
@click.option("--environment", type=click.Choice(["invoke", "dda", "all"]), default="all", help="Type of dependencies to show")
@pass_app
def cmd(app: Application, *, environment: str) -> None:
    """
    Show all installed dependencies.

    Example:

    ```
    dda self dep show
    ```
    """

    if environment == "invoke" or environment == "all":
        click.echo("=== Invoke dependencies ===")
        venv_path = app.config.storage.join("venvs", "legacy").data
        with app.tools.uv.virtual_env(venv_path) as venv:
            click.echo(get_installed_dependencies(app=app, prefix=str(venv.path)))

    if environment == "dda" or environment == "all":
        if environment == "all":
            click.echo("\n\n")

        click.echo("=== DDA dependencies ===")
        click.echo(get_installed_dependencies(app=app))
