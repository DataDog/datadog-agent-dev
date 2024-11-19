# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from deva.cli.application import Application


@click.command(short_help='Build documentation')
@click.option('--check', is_flag=True, help='Ensure links are valid')
@click.pass_obj
def cmd(app: Application, check):
    """
    Build documentation.
    """
    script = 'build-check' if check else 'build'
    app.platform.exit_with_command([sys.executable, '-m', 'hatch', 'run', f'docs:{script}'])
