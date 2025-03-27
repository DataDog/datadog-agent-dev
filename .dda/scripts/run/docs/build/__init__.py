# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Build documentation", features=["dev"])
@click.option("--check", is_flag=True, help="Ensure links are valid")
@click.pass_obj
def cmd(app: Application, *, check: bool) -> None:
    """
    Build documentation.
    """
    script = "build-check" if check else "build"
    app.subprocess.exit_with_command([sys.executable, "-m", "hatch", "run", f"docs:{script}"])
