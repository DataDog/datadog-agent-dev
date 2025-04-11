# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, ensure_features_installed, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Synchronize dependencies")
@click.option("-f", "--feature", "features", multiple=True, help="Feature to synchronize (multiple allowed)")
@pass_app
def cmd(app: Application, *, features: tuple[str, ...]) -> None:
    """
    Synchronize dependencies.

    Example:

    ```
    dda self dep sync -f foo -f bar
    ```
    """
    ensure_features_installed(list(features), app=app)
