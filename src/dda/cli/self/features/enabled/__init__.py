# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


def _parse_scopes(values: tuple[str, ...]) -> dict[str, str]:
    scopes: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            err_message = f"Invalid scope '{item}', expected key=value"
            raise click.BadParameter(err_message)
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            err_message = f"Invalid scope '{item}', key cannot be empty"
            raise click.BadParameter(err_message)
        scopes[key] = value
    return scopes


@dynamic_command(short_help="Evaluate a feature flag")
@click.argument("flag", metavar="FLAG", type=str)
@click.option(
    "--default",
    "default_value",
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
    metavar="KEY=VALUE",
    help="Additional targeting attributes. Can be specified multiple times.",
)
@pass_app
def cmd(app: Application, *, flag: str, default_value: bool, scopes: tuple[str, ...]) -> None:
    """
    Evaluate an arbitrary feature flag and print the result as 'true' or 'false'.

    Examples:
      dda self feature enabled my-flag
      dda self feature enabled my-flag --default true
      dda self feature enabled my-flag --scope env=ci --scope team=agent
    """
    extra_scopes = _parse_scopes(scopes)
    enabled = app.features.enabled(flag, default=default_value, scopes=extra_scopes or None)
    app.display("true" if enabled else "false")
