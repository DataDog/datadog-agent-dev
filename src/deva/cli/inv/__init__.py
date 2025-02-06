# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command, ensure_features_installed
from deva.config.constants import AppEnvVars

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(
    short_help="Invoke a local task",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", nargs=-1)
@click.option(
    "--no-dynamic-deps",
    envvar=AppEnvVars.NO_DYNAMIC_DEPS,
    is_flag=True,
    help="Assume required dependencies are already installed",
)
@click.pass_obj
def cmd(app: Application, *, args: tuple[str, ...], no_dynamic_deps: bool) -> None:
    """
    Invoke a local task.
    """
    from deva.utils.fs import Path

    features = ["legacy-tasks"]
    invoke_args = [arg for arg in args if not arg.startswith("-")]
    if invoke_args:
        task = invoke_args[0]
        if Path.cwd().name == "test-infra-definitions":
            features.append("legacy-test-infra-definitions")
        elif task.startswith("system-probe."):
            features.append("legacy-btf-gen")
        elif task.startswith("kmt."):
            features.append("legacy-kernel-matrix-testing")

    if no_dynamic_deps:
        import sys

        app.subprocess.replace_current_process([sys.executable, "-m", "invoke", *args])
        return

    venv_path = app.config.storage.join("venvs", "legacy").data
    with app.tools.uv.virtual_env(venv_path) as venv:
        ensure_features_installed(
            features,
            app=app,
            prefix=str(venv.path),
        )
        app.subprocess.replace_current_process(["python", "-m", "invoke", *args])
