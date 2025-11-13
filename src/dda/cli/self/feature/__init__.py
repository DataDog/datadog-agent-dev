# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.types.hooks import enc_hook

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Evaluate a feature flag")
@click.argument("flag")
@click.option(
    "--default",
    type=bool,
    default=False,
    show_default=True,
    help="Default value to use if the flag cannot be evaluated.",
)
@click.option(
    "-s",
    "--scope",
    "scopes",
    multiple=True,
    type=(str, str),
    help="Additional targeting attributes. Can be specified multiple times.",
)
@click.option(
    "--json",
    is_flag=True,
    help="Output result as JSON with value, defaulted status, and error message.",
)
@pass_app
def cmd(app: Application, *, flag: str, default: bool, scopes: tuple[tuple[str, str], ...], json: bool) -> None:
    """
    Evaluate an arbitrary feature flag and print the result as 'true' or 'false'.

    Examples:
      dda self feature enabled my-flag
      dda self feature enabled my-flag --default true
      dda self feature enabled my-flag --scope env ci --scope team agent
    """
    extra_scopes = dict(scopes) if scopes else None

    feature_flag_result = app.features.enabled(flag, default=default, scopes=extra_scopes)
    if json:
        from msgspec import json as json_lib

        app.display(json_lib.encode(feature_flag_result.to_dict(), enc_hook=enc_hook).decode("utf-8"))
    else:
        app.display(f"{feature_flag_result.value}")
