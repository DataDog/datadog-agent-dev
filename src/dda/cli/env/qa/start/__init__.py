# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command
from dda.cli.env.qa.utils import get_env_type, option_env_type
from dda.env.qa import get_qa_env

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.cli.base import DynamicContext


def resolve_environment(ctx: DynamicContext, param: click.Option, value: str) -> str:
    from msgspec_click import generate_options

    env_type = get_env_type(ctx, param, value)
    env_class = get_qa_env(env_type)
    ctx.dynamic_params.extend(generate_options(env_class.config_class()))
    return env_type


@dynamic_command(
    short_help="Start a QA environment",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
@option_env_type(callback=resolve_environment)
@click.option("--id", "instance", default="default", help="Unique identifier for the environment")
@click.option(
    "-c",
    "--config",
    "config_template_name",
    default="default",
    help="The name of the Agent config template to use",
)
@click.pass_context
def cmd(ctx: click.Context, *, env_type: str, instance: str, config_template_name: str) -> None:
    """
    Start a QA environment.
    """
    import msgspec

    from dda.env.config.agent import AgentConfigTemplates
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
    if "e2e" not in user_config and app.config.env.qa.e2e:
        user_config["e2e"] = True

    agent_config_templates = AgentConfigTemplates(app)
    template = agent_config_templates.get(config_template_name)
    if not template.exists():
        if config_template_name != "default":
            app.abort(f"Agent config template not found: {config_template_name}")

        template.restore_defaults()

    env_class = get_qa_env(env_type)
    config = msgspec.convert(user_config, env_class.config_class())
    env = env_class(
        app=app,
        name=env_type,
        instance=instance,
        config=config,
        agent_config_template_path=template.root_dir,
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
            f"Cannot start QA environment `{instance}` of type `{env_type}` in state `{status.state}`, "
            f"must be one of: {', '.join(sorted(transition_states))}"
        )

    env.save_state()
    try:
        env.start()
    except Exception:
        env.remove_state()
        raise
