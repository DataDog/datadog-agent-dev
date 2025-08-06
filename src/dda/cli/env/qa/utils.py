# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import click

from dda.env.qa import AVAILABLE_QA_ENVS, DEFAULT_QA_ENV

if TYPE_CHECKING:
    from dda.cli.application import Application


def get_env_type(ctx: click.Context, param: click.Option, value: str | None) -> str:
    if value:
        return value

    app: Application = ctx.obj
    env_type = app.config.env.qa.default_type or DEFAULT_QA_ENV
    param.default = env_type
    return env_type


option_env_type = partial(
    click.option,
    "--type",
    "-t",
    "env_type",
    type=click.Choice(AVAILABLE_QA_ENVS),
    show_default=True,
    is_eager=True,
    callback=get_env_type,
    help="The type of QA environment",
)
