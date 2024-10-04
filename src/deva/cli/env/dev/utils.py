# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import click

from deva.env.dev import AVAILABLE_DEV_ENVS, DEFAULT_DEV_ENV

if TYPE_CHECKING:
    from deva.cli.application import Application


def get_env_type(value: str | None, ctx: click.Context) -> str:
    if value:
        return value

    app: Application = ctx.obj
    return app.config.env.dev.default_type or DEFAULT_DEV_ENV


def option_env_type_callback(ctx: click.Context, param: click.Option, value: str | None) -> str:  # noqa: ARG001
    from deva.cli.env.dev.utils import get_env_type

    return get_env_type(value, ctx)


option_env_type = partial(
    click.option,
    "--type",
    "-t",
    "env_type",
    type=click.Choice(AVAILABLE_DEV_ENVS),
    show_default=True,
    is_eager=True,
    callback=option_env_type_callback,
    help="The type of developer environment",
)
