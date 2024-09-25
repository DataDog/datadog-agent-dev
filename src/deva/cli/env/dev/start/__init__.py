# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from deva.cli.base import dynamic_command
from deva.cli.env.dev.utils import get_env_type, option_env_type
from deva.env.dev import get_dev_env

if TYPE_CHECKING:
    from deva.cli.application import Application
    from deva.cli.base import DynamicContext


def resolve_environment(ctx: DynamicContext, param: click.Option, value: str) -> str:  # noqa: ARG001
    from msgspec_click import generate_options

    env_type = get_env_type(value, ctx)
    env_class = get_dev_env(env_type)
    ctx.dynamic_params.extend(generate_options(env_class.config_class()))
    return env_type


@dynamic_command(short_help="Start a developer environment", context_settings={"ignore_unknown_options": True})
@option_env_type(callback=resolve_environment)
@click.pass_context
def cmd(ctx: click.Context, env_type: str, **kwargs: Any) -> None:
    """
    Start a developer environment.
    """
    import msgspec

    from deva.env.models import EnvironmentStage

    app: Application = ctx.obj
    user_config = dict(app.config.envs.get(env_type, {}))
    user_config.update(kwargs)

    env_class = get_dev_env(env_type)
    config = msgspec.convert(user_config, env_class.config_class())
    env = env_class(
        app=app,
        name=env_type,
        config=config,
    )
    if kwargs and env.config_file.is_file():
        options = ", ".join(sorted(kwargs))
        app.abort(
            f"Ignoring the following options as environments cannot be reconfigured from a stopped state: {options}\n"
            f"To change the configuration, you must remove the environment after stopping it."
        )

    status = env.status()
    expected_stage = EnvironmentStage.INACTIVE
    if status.stage != expected_stage:
        app.abort(
            f"Cannot start developer environment `{env_type}` in stage `{status.stage}`, must be `{expected_stage}`"
        )

    env.start()
    env.save_config()