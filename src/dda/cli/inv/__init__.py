# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, ensure_deps_installed, ensure_features_installed
from dda.config.constants import AppEnvVars

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="Invoke a local task",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", nargs=-1, required=False)
@click.option(
    "--feat",
    "extra_features",
    multiple=True,
    help="""\
Extra features to install (multiple allowed).
After a feature is installed once, it will always be available.
""",
)
@click.option(
    "--dep",
    "extra_dependencies",
    multiple=True,
    help="""\
Extra dependencies to install (multiple allowed).
After a dependency is installed once, it will always be available.
""",
)
@click.option(
    "--no-dynamic-deps",
    envvar=AppEnvVars.NO_DYNAMIC_DEPS,
    is_flag=True,
    help="Assume required dependencies are already installed",
)
@click.pass_context
def cmd(
    ctx: click.Context,
    *,
    args: tuple[str, ...],
    extra_features: tuple[str, ...],
    extra_dependencies: tuple[str, ...],
    no_dynamic_deps: bool,
) -> None:
    """
    Invoke a local task.
    """
    from dda.utils.fs import Path

    app: Application = ctx.obj

    if not args:
        app.display(ctx.get_help())
        return

    features = ["legacy-tasks", *extra_features]
    invoke_args = [arg for arg in args if not arg.startswith("-")]
    if invoke_args:
        task = invoke_args[0]
        if Path.cwd().name == "test-infra-definitions":
            features.append("legacy-test-infra-definitions")
        elif task.startswith("system-probe."):
            features.append("legacy-btf-gen")

    if no_dynamic_deps:
        import sys

        app.subprocess.exit_with([sys.executable, "-m", "invoke", *args])

    venv_path = app.config.storage.join("venvs", "legacy").data
    with app.tools.uv.virtual_env(venv_path) as venv:
        ensure_features_installed(
            features,
            app=app,
            prefix=str(venv.path),
        )
        if extra_dependencies:
            ensure_deps_installed(list(extra_dependencies), app=app, sys_path=venv.get_sys_path(app))

        app.subprocess.exit_with(["python", "-m", "invoke", *args])
