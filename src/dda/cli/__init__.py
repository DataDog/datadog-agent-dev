# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from time import perf_counter_ns
from typing import TYPE_CHECKING

START_TIME = perf_counter_ns()

import os
import sys

import rich_click as click

from dda._version import __version__
from dda.cli.base import dynamic_group
from dda.config.constants import AppEnvVars, ConfigEnvVars

if TYPE_CHECKING:
    from dda.config.file import ConfigFile


def search_path_finder() -> list[str]:
    search_paths = []

    commands_dir = os.path.join(os.getcwd(), ".dda", "extend", "commands")
    if os.path.isdir(commands_dir):
        search_paths.append(commands_dir)

    return search_paths


def set_default_config(
    config: ConfigFile,
    *,
    verbose: int | None,
    quiet: int | None,
    data_dir: str | None,
    cache_dir: str | None,
) -> None:
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


@dynamic_group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120, "show_default": True},
    invoke_without_command=True,
    allow_external_plugins=True,
    search_path_finder=search_path_finder,
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
    help="Increase verbosity (can be used additively) [env var: `DDA_VERBOSE`]",
)
@click.option(
    "--quiet",
    "-q",
    envvar=AppEnvVars.QUIET,
    count=True,
    default=None,
    help="Decrease verbosity (can be used additively) [env var: `DDA_QUIET`]",
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
        "[env var: `DDA_INTERACTIVE`]"
    ),
)
@click.option(
    "--data-dir",
    envvar=ConfigEnvVars.DATA,
    help="The path to a custom directory used to persist data [env var: `DDA_DATA_DIR`]",
)
@click.option(
    "--cache-dir",
    envvar=ConfigEnvVars.CACHE,
    help="The path to a custom directory used to cache data [env var: `DDA_CACHE_DIR`]",
)
@click.option(
    "--config",
    "config_file",
    envvar=ConfigEnvVars.CONFIG,
    help="The path to a custom config file to use [env var: `DDA_CONFIG`]",
)
@click.version_option(version=__version__, prog_name="dda")
@click.pass_context
def dda(
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
    \b
    ```
         _     _
      __| | __| | __ _
     / _` |/ _` |/ _` |
    | (_| | (_| | (_| |
     \\__,_|\\__,_|\\__,_|
    ```
    """
    import msgspec

    from dda.cli.application import Application
    from dda.config.file import ConfigFile
    from dda.utils.ci import running_in_ci
    from dda.utils.fs import Path

    config = ConfigFile(config_file)
    if not config.path.is_file():
        config.restore()

    set_default_config(config, verbose=verbose, quiet=quiet, data_dir=data_dir, cache_dir=cache_dir)

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
            set_default_config(config, verbose=verbose, quiet=quiet, data_dir=data_dir, cache_dir=cache_dir)
        else:
            ctx.fail(f"Error loading config: {config.path}\n{e}")

    app = Application(terminator=ctx.exit, config_file=config, enable_color=color, interactive=interactive)

    # Persist app data for sub-commands
    ctx.obj = app

    # Telemetry submission
    if not app.telemetry.consent_recorded() and app.console.is_interactive:
        if app.confirm(
            "Would you like to enable telemetry to help improve the tool (only works for Datadog employees)"
        ):
            app.telemetry.consent()
        else:
            app.telemetry.dissent()

    app.telemetry.submit_data("start_time", str(START_TIME))
    app.telemetry.submit_data("command", str(sys.argv[1:]))

    if not ctx.invoked_subcommand:
        app.output(ctx.get_help())
        app.abort(code=0)

    cwd = Path.cwd()
    if (version_file := cwd / ".dda-version").is_file() or (version_file := cwd / ".dda" / "version").is_file():
        pinned_version = version_file.read_text().strip()
        pinned_version_parts = list(map(int, pinned_version.split(".")))
        # Limit to X.Y.Z in case of dev versions e.g. 1.2.3.dev1
        current_version_parts = list(map(int, __version__.split(".")[:3]))

        if current_version_parts < pinned_version_parts:
            app.display_critical(f"Repo requires at least dda version {pinned_version} but {__version__} is installed.")
            if app.managed_installation:
                app.display("Run the following command:\ndda self update")

            app.abort()


def main() -> None:
    try:
        dda(prog_name="dda", windows_expand_args=False)
    except Exception:  # noqa: BLE001
        import os
        import sys

        import click as click_core
        from rich.console import Console

        console = Console()
        dda_debug = os.getenv("DDA_DEBUG") in {"1", "true"}
        console.print_exception(suppress=[click, click_core], show_locals=dda_debug)
        sys.exit(1)
