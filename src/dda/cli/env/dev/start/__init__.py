# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command
from dda.cli.env.dev.utils import get_env_type, option_env_type
from dda.env.dev import get_dev_env

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.cli.base import DynamicContext


def resolve_environment(ctx: DynamicContext, param: click.Option, value: str) -> str:
    from msgspec_click import generate_options

    env_type = get_env_type(ctx, param, value)
    env_class = get_dev_env(env_type)
    ctx.dynamic_params.extend(generate_options(env_class.config_class()))
    return env_type


@dynamic_command(
    short_help="Start a developer environment",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
@option_env_type(callback=resolve_environment)
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.pass_context
def cmd(ctx: click.Context, *, env_type: str, instance: str) -> None:
    """
    Start a developer environment.
    """
    import msgspec

    from dda.env.models import EnvironmentState

    app: Application = ctx.obj

    dynamic_context = ctx.get_dynamic_sibling()  # type: ignore[attr-defined]
    dynamic_options = {
        param: value
        for param, value in dynamic_context.params.items()
        if dynamic_context.get_parameter_source(param).name != "DEFAULT"
    }
    user_config = dict(app.config.envs.get(env_type, {}))
    user_config.update(dynamic_options)
    if "clone" not in user_config and app.config.env.dev.clone_repos:
        user_config["clone"] = True
    if "shell" not in user_config and app.config.env.dev.universal_shell:
        user_config["shell"] = "nu"

    env_class = get_dev_env(env_type)
    config = msgspec.convert(user_config, env_class.config_class())
    env = env_class(
        app=app,
        name=env_type,
        instance=instance,
        config=config,
    )
    if dynamic_options and env.config_file.is_file():
        options = ", ".join(sorted(dynamic_options))
        app.abort(
            f"Ignoring the following options as environments cannot be reconfigured from a stopped state: {options}\n"
            f"To change the configuration, you must remove the environment after stopping it."
        )

    status = env.status()
    transition_states = {EnvironmentState.NONEXISTENT, EnvironmentState.STOPPED}
    if status.state not in transition_states:
        app.abort(
            f"Cannot start developer environment `{env_type}` in state `{status.state}`, must be one of: "
            f"{', '.join(sorted(transition_states))}"
        )

    env.start()
    env.save_config()
