# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from deva.cli.base import dynamic_command

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(
    short_help="Lock dependencies",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", nargs=-1)
@click.pass_obj
def cmd(app: Application, *, args: tuple[str, ...]) -> None:
    """
    Lock dependencies.
    """
    from importlib import resources
    from importlib.metadata import distribution

    from packaging.specifiers import SpecifierSet

    from deva.utils.fs import Path
    from deva.utils.process import EnvVars

    minor_version: int | None = None
    requires_python = distribution("datadog-agent-dev").metadata["Requires-Python"]
    python_constraint = SpecifierSet(requires_python)
    for i in range(100):
        if python_constraint.contains(f"3.{i}"):
            minor_version = i
        elif minor_version is not None:
            break
    else:  # no cov
        app.abort(
            f"""\
Failed to find a valid Python version in project metadata:
requires-python = "{requires_python}"\
"""
        )

    with EnvVars({"DOCKER_CLI_HINTS": "false"}):
        app.tools.docker.run([
            "build",
            "--build-arg",
            f"PYTHON_VERSION=3.{minor_version}",
            "--tag",
            "deva-lock-deps",
            "-f",
            str(resources.files("deva.cli.self.dep.lock").joinpath("Dockerfile")),
            ".",
        ])
        app.tools.docker.run([
            "run",
            "--rm",
            "-t",
            "-v",
            f"{Path.cwd()}:/app",
            "deva-lock-deps",
            *args,
        ])
