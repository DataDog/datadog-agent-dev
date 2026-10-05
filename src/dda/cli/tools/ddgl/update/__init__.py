import click

from dda.cli.application import Application
from dda.cli.base import dynamic_command, pass_app


@dynamic_command(short_help="Upgrade ddgl, optionally to a specific version.")
@click.argument("version", required=False, help="The specific version or git ref to install")
@click.option("--git", "-g", is_flag=True, help="Use this flag if you are trying to upgrade to a specific git ref or a version not yet release on PyPI.")
@pass_app
def cmd(app: Application, *, git: bool, version: str | None = None) -> None:
    package = "ddgl" if not git else "https://github.com/DataDog/ddgl-cli"
    if version:
        if git:
            package += f"@{version}"
        else:
            package += f"=={version}"
    app.tools.uv.upgrade_tool(package)
