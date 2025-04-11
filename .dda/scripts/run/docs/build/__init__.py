# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Build documentation", features=["self-dev"])
@click.argument("args", nargs=-1)
@click.option("--check", is_flag=True, help="Ensure links are valid")
@pass_app
def cmd(app: Application, *, args: tuple[str, ...], check: bool) -> None:
    """
    Build documentation.
    """
    script = "build-check" if check else "build"
    app.subprocess.exit_with([sys.executable, "-m", "hatch", "run", f"docs:{script}", *args])
