# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def test_local_command(dda, helpers, temp_dir):
    scripts_dir = temp_dir / ".dda" / "scripts"
    scripts_dir.ensure_dir()
    scripts_dir.joinpath("_utils").ensure_dir()
    scripts_dir.joinpath("_utils", "__init__.py").touch()
    scripts_dir.joinpath("_utils", "foo.py").write_text(
        helpers.dedent(
            """
            bar = "baz"
            """
        )
    )
    scripts_dir.joinpath("config").ensure_dir()
    scripts_dir.joinpath("config", "__init__.py").touch()
    scripts_dir.joinpath("config", "foo").ensure_dir()
    scripts_dir.joinpath("config", "foo", "__init__.py").write_text(
        helpers.dedent(
            """
            import click
            from dda.cli.base import dynamic_command, pass_app

            @dynamic_command()
            @pass_app
            def cmd(app):
                from _utils import foo

                app.display(f"{foo.bar=}")
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
