# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import subprocess
import sys
from unittest import mock


def test_local_command(dda, helpers, temp_dir):
    commands_dir = temp_dir / ".dda" / "extend" / "commands"
    commands_dir.ensure_dir()
    commands_dir.joinpath("config").ensure_dir()
    commands_dir.joinpath("config", "__init__.py").touch()
    commands_dir.joinpath("config", "foo").ensure_dir()
    commands_dir.joinpath("config", "foo", "__init__.py").write_text(
        helpers.dedent(
            """
            from dda.cli.base import dynamic_command, pass_app

            from utils import bar

            @dynamic_command()
            @pass_app
            def cmd(app):
                from utils import foo

                app.display(f"{foo.bar=}")
                app.display(f"{bar.baz=}")
            """
        )
    )
    pythonpath = commands_dir.parent / "pythonpath"
    pythonpath.ensure_dir()
    pythonpath.joinpath("utils").ensure_dir()
    pythonpath.joinpath("utils", "__init__.py").touch()
    pythonpath.joinpath("utils", "bar.py").write_text(
        helpers.dedent(
            """
            baz = "qux"
            """
        )
    )
    pythonpath.joinpath("utils", "foo.py").write_text(
        helpers.dedent(
            """
            bar = "baz"
            """
        )
    )

    with temp_dir.as_cwd():
        result = dda("config", "foo")

    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            """
            foo.bar='baz'
            bar.baz='qux'
            """
        ),
    )

    with temp_dir.as_cwd():
        result = dda()

    result.check_exit_code(0)
    assert "utils" not in result.stdout


def test_dependencies(dda, helpers, temp_dir, uv_on_path, mocker):
    subprocess_run = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], returncode=0))

    commands_dir = temp_dir / ".dda" / "extend" / "commands"
    commands_dir.ensure_dir()
    commands_dir.joinpath("foo").ensure_dir()
    commands_dir.joinpath("foo", "__init__.py").write_text(
        helpers.dedent(
            f"""
            from dda.cli.base import dynamic_command, pass_app

            @dynamic_command(dependencies=["{os.urandom(10).hex()}"])
            @pass_app
            def cmd(app):
                app.display("foo")
            """
        )
    )

    with temp_dir.as_cwd():
        result = dda("foo")

    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            """
            foo
            """
        ),
        output=helpers.dedent(
            """
            Synchronizing dependencies
            foo
            """
        ),
    )

    expected_path = str(uv_on_path.with_stem(f"{uv_on_path.stem}-{uv_on_path.id}"))
    assert subprocess_run.call_args_list == [
        mock.call(
            [
                expected_path,
                "pip",
                "install",
                "--python",
                sys.executable,
                "-r",
                mocker.ANY,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        ),
    ]
