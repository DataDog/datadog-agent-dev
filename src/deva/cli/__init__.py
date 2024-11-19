# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os

import rich_click as click

from deva._version import __version__
from deva.cli.base import dynamic_group
from deva.config.constants import AppEnvVars, ConfigEnvVars


@dynamic_group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120},
    invoke_without_command=True,
    external_plugins=True,
    subcommands=(
        "celian",
        "config",
        "env",
        "log",
    ),
)
@click.rich_config(
    help_config=click.RichHelpConfiguration(
        use_markdown=True,
        show_metavars_column=False,
        append_metavars_help=True,
        style_option="purple",
        style_argument="purple",
        style_command="purple",
    ),
)
@click.option(
    "--verbose",
    "-v",
    envvar=AppEnvVars.VERBOSE,
    count=True,
    default=None,
    help="Increase verbosity (can be used additively) [env var: `DEVA_VERBOSE`]",
)
@click.option(
    "--quiet",
    "-q",
    envvar=AppEnvVars.QUIET,
    count=True,
    default=None,
    help="Decrease verbosity (can be used additively) [env var: `DEVA_QUIET`]",
)
@click.option(
    "--color/--no-color",
    default=None,
    help="Whether or not to display colored output (default is auto-detection) [env vars: `FORCE_COLOR`/`NO_COLOR`]",
)
@click.option(
    "--interactive/--no-interactive",
    envvar=AppEnvVars.INTERACTIVE,
    default=None,
    help=(
        "Whether or not to allow features like prompts and progress bars (default is auto-detection) "
        "[env var: `DEVA_INTERACTIVE`]"
    ),
)
@click.option(
    "--data-dir",
    envvar=ConfigEnvVars.DATA,
    help="The path to a custom directory used to persist data [env var: `DEVA_DATA_DIR`]",
)
@click.option(
    "--cache-dir",
    envvar=ConfigEnvVars.CACHE,
    help="The path to a custom directory used to cache data [env var: `DEVA_CACHE_DIR`]",
)
@click.option(
    "--config",
    "config_file",
    envvar=ConfigEnvVars.CONFIG,
    help="The path to a custom config file to use [env var: `DEVA_CONFIG`]",
)
@click.version_option(version=__version__, prog_name="deva")
@click.pass_context
def deva(
    ctx: click.Context,
    *,
    verbose: int | None,
    quiet: int | None,
    color: bool | None,
    interactive: bool | None,
    data_dir: str | None,
    cache_dir: str | None,
    config_file: str | None,
) -> None:
    """
    ```
         _
      __| | _____   ____ _
     / _` |/ _ \\ \\ / / _` |
    | (_| |  __/\\ V / (_| |
     \\__,_|\\___| \\_/ \\__,_|
    ```
    """
    import msgspec

    from deva.cli.application import Application
    from deva.config.file import ConfigFile
    from deva.utils.ci import running_in_ci

    config = ConfigFile(config_file)
    if not config.path.is_file():
        config.restore()

    if verbose is not None or quiet is not None:
        verbosity = 0
        if verbose is not None:
            verbosity += verbose
        if quiet is not None:
            verbosity -= quiet

        config.data.setdefault("terminal", {})["verbosity"] = verbosity

    if data_dir is not None:
        config.data.setdefault("storage", {})["data"] = data_dir

    if cache_dir is not None:
        config.data.setdefault("storage", {})["cache"] = cache_dir

    if color is None:
        if os.environ.get(AppEnvVars.NO_COLOR) == "1":
            color = False
        elif os.environ.get(AppEnvVars.FORCE_COLOR) == "1":
            color = True

    if interactive is None and running_in_ci():
        interactive = False

    try:
        _ = config.model
    except msgspec.ValidationError as e:
        # Allow the user to modify the config if it's invalid
        if ctx.invoked_subcommand == "config":
            config.data.clear()
        else:
            ctx.fail(f"Error loading config: {config.path}\n{e}")

    app = Application(terminator=ctx.exit, config_file=config, enable_color=color, interactive=interactive)
    if not ctx.invoked_subcommand:
        app.output(ctx.get_help())
        app.abort(code=0)

    # Persist app data for sub-commands
    ctx.obj = app


def main() -> None:
    try:
        deva(prog_name="deva", windows_expand_args=False)
    except Exception:  # noqa: BLE001
        import os
        import sys

        import click as click_core
        from rich.console import Console

        console = Console()
        deva_debug = os.getenv("DEVA_DEBUG") in {"1", "true"}
        console.print_exception(suppress=[click, click_core], show_locals=deva_debug)
        sys.exit(1)
