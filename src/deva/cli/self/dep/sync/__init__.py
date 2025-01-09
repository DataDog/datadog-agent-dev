# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command, ensure_features_installed

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(short_help="Synchronize dependencies")
@click.option("-f", "--feature", "features", multiple=True, help="Feature to synchronize (multiple allowed)")
@click.pass_obj
def cmd(app: Application, *, features: tuple[str, ...]) -> None:
    """
    Synchronize dependencies.

    Example:

    ```
    deva self dep sync -f foo -f bar
    ```
    """
    ensure_features_installed(list(features), app=app)
