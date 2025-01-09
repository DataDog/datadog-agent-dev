# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess
import sys
from unittest import mock

import pytest

from deva.config.constants import AppEnvVars
from deva.utils.process import EnvVars

pytestmark = [pytest.mark.usefixtures("private_storage")]


def test_default(deva, helpers, temp_dir, uv_on_path, mocker):
    replace_current_process = mocker.patch("deva.utils.process.SubprocessRunner.replace_current_process")
    subprocess_run = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], returncode=0))

    result = deva("inv", "foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Creating virtual environment
        Synchronizing dependencies
        """
    )

    assert subprocess_run.call_args_list == [
        mock.call(
            [
                uv_on_path,
                "venv",
                str(temp_dir / "data" / "venvs" / "legacy"),
                "--seed",
                "--python",
                sys.executable,
            ],
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ),
        mock.call(
            [
                uv_on_path,
                "sync",
                "--frozen",
                "--no-install-project",
                "--inexact",
                "--only-group",
                "legacy-tasks",
            ],
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=mock.ANY,
            env=mock.ANY,
        ),
    ]
    assert replace_current_process.call_args_list == [
        mock.call(
            [
                "python",
                "-m",
                "invoke",
                "foo",
            ],
        )
    ]


def test_no_dynamic_deps_flag(deva, mocker):
    replace_current_process = mocker.patch("deva.utils.process.SubprocessRunner.replace_current_process")

    result = deva("inv", "--no-dynamic-deps", "foo")

    assert result.exit_code == 0, result.output
    assert not result.output

    assert replace_current_process.call_args_list == [
        mock.call(
            [
                "python",
                "-m",
                "invoke",
                "foo",
            ],
        )
    ]


def test_no_dynamic_deps_env_var(deva, mocker):
    replace_current_process = mocker.patch("deva.utils.process.SubprocessRunner.replace_current_process")

    with EnvVars({AppEnvVars.NO_DYNAMIC_DEPS: "1"}):
        result = deva("inv", "foo")

    assert result.exit_code == 0, result.output
    assert not result.output

    assert replace_current_process.call_args_list == [
        mock.call(
            [
                "python",
                "-m",
                "invoke",
                "foo",
            ],
        )
    ]
