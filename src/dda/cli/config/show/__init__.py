# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Render the contents of the config file")
@click.option("--all", "-a", "all_keys", is_flag=True, help="Do not scrub secret fields")
@click.pass_obj
def cmd(app: Application, *, all_keys: bool) -> None:
    """Render the contents of the config file."""
    text = app.config_file.read() if all_keys else app.config_file.read_scrubbed()
    app.display_syntax(text.rstrip(), "toml")
