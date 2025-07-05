# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Show installed dependencies")
@click.option("--legacy", is_flag=True, help="Only show legacy invoke dependencies")
@pass_app
def cmd(app: Application, *, legacy: bool) -> None:
    """
    Show all installed dependencies.

    Example:

    ```
    dda self dep show
    ```
    """
    import sys

    if legacy:
        venv_path = app.config.storage.join("venvs", "legacy").data
        with app.tools.uv.virtual_env(venv_path):
            app.tools.uv.exit_with(["pip", "tree"])
    else:
        app.tools.uv.exit_with(["pip", "tree", "--python", sys.executable])
