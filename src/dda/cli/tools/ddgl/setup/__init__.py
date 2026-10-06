import click

from dda.cli.application import Application
from dda.cli.base import dynamic_command, pass_app
from dda.utils.platform import which


def _check_ddgl() -> bool:
    """Check if ddgl is installed and available on $PATH"""
    out = which("ddgl") or ""
    return len(out.strip()) > 0


@dynamic_command(short_help="Setup ddgl, creating a config file and adding it to PATH")
@click.option("--dev", is_flag=True, help="Use the latest dev version of ddgl from `main`.")
@click.option("--ref", help="Use ddgl from a specific git ref", default=None)
@click.option("--no-config", is_flag=True, help="Don't overwrite or drop a config file")
@click.option("--force", is_flag=True, help="Force install and overwrite config file")
@pass_app
def cmd(app: Application, *, ref: str | None, dev: bool, no_config: bool, force: bool) -> None:
    if not force and _check_ddgl():
        app.abort(
            "ddgl is already installed. Use --force to reinstall and reset config or `dda tool ddgl update` to update.",
            code=0,
        )

    # Early-exit if ddtool is not on PATH, since the config we drop relies on it for creating gitlab tokens
    if not which("ddtool"):
        app.abort(
            "`ddtool` not found on PATH. This command is only meant for Datadog employees with access to `ddtool`. Please install it using `dogbrew install ddtool`",
            code=1,
        )

    if dev:
        ref = "main"

    # Use a specific git ref if provided or use latest release on PyPI
    package = f"git+https://github.com/DataDog/ddgl-cli@{ref}" if ref else "ddgl"

    app.tools.uv.install_tool(package, force=force)

    # Make sure ddgl is in path
    if not _check_ddgl():
        app.abort("ddgl not found in $PATH after install. Maybe run `uv tool update-shell` ?")

    if not no_config:
        from dda.utils.fs import Path

        ddgl_config_path = Path(app.subprocess.capture(["ddgl", "config", "path"]).strip())
        if not force and ddgl_config_path.exists():
            app.display_info(f"Config file found at {ddgl_config_path}, not overwriting. Use --force to overwrite.")
            return

        # Overwrite the existing file
        ddgl_config_path.write_text(
            """
            gitlab_url="https://gitlab.ddbuild.io"
            github_fallback = true
            token_command = ["ddtool", "auth", "gitlab", "token"]
            """
        )
