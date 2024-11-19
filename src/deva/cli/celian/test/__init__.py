# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command
from deva.utils import logging

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(short_help="Test")
@click.pass_obj
def cmd(app: Application) -> None:
    """Test."""
    logging.error('My error message')

