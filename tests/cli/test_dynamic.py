# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def test_local_command(dda, helpers, temp_dir):
    commands_dir = temp_dir / ".dda" / "extend" / "commands"
    commands_dir.ensure_dir()
    commands_dir.joinpath("config").ensure_dir()
    commands_dir.joinpath("config", "__init__.py").touch()
    commands_dir.joinpath("config", "foo").ensure_dir()
    commands_dir.joinpath("config", "foo", "__init__.py").write_text(
        helpers.dedent(
            """
            import click
            from dda.cli.base import dynamic_command, pass_app

            @dynamic_command()
            @pass_app
            def cmd(app):
                from utils import foo

                app.display(f"{foo.bar=}")
            """
        )
    )
    pythonpath = commands_dir.parent / "pythonpath"
    pythonpath.ensure_dir()
    pythonpath.joinpath("utils").ensure_dir()
    pythonpath.joinpath("utils", "__init__.py").touch()
    pythonpath.joinpath("utils", "foo.py").write_text(
        helpers.dedent(
            """
            bar = "baz"
            """
        )
    )

    with temp_dir.as_cwd():
        result = dda("config", "foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        foo.bar='baz'
        """
    )

    with temp_dir.as_cwd():
        result = dda()

    assert result.exit_code == 0, result.output
    assert "utils" not in result.output
