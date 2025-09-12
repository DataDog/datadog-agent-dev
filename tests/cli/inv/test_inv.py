# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from dda.config.constants import AppEnvVars
from dda.utils.process import EnvVars

pytestmark = [pytest.mark.usefixtures("private_storage")]


def test_default(dda, helpers, temp_dir, uv_on_path, mocker):
    exit_with = mocker.patch(
        "dda.utils.process.SubprocessRunner.exit_with",
        side_effect=lambda *args, **kwargs: sys.exit(0),  # noqa: ARG005
    )
    subprocess_run = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], returncode=0))

    result = dda("inv", "foo")
    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            Creating virtual environment
            Synchronizing dependencies
            """
        ),
    )

    expected_name = uv_on_path.with_stem(f"{uv_on_path.stem}-{uv_on_path.id}").name
    first_call, second_call = subprocess_run.call_args_list

    assert Path(first_call.args[0][0]).name == expected_name
    assert first_call == mock.call(
        [
            mock.ANY,
            "venv",
            str(temp_dir / "data" / "venvs" / "legacy"),
            "--seed",
            "--python",
            sys.executable,
        ],
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert Path(second_call.args[0][0]).name == expected_name
    assert second_call == mock.call(
        [
            mock.ANY,
            "sync",
            "--frozen",
            "--no-install-project",
            "--inexact",
            "--only-group",
            "legacy-tasks",
        ],
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=mock.ANY,
        env=mock.ANY,
    )
    assert exit_with.call_args_list == [
        mock.call(
            [
                "python",
                "-m",
                "invoke",
                "foo",
            ],
        )
    ]


def test_no_dynamic_deps_flag(dda, mocker):
    exit_with = mocker.patch(
        "dda.utils.process.SubprocessRunner.exit_with",
        side_effect=lambda *args, **kwargs: sys.exit(0),  # noqa: ARG005
    )

    result = dda("inv", "--no-dynamic-deps", "foo")
    result.check(exit_code=0)

    assert exit_with.call_args_list == [
        mock.call(
            [
                sys.executable,
                "-m",
                "invoke",
                "foo",
            ],
        )
    ]


def test_no_dynamic_deps_env_var(dda, mocker):
    exit_with = mocker.patch(
        "dda.utils.process.SubprocessRunner.exit_with",
        side_effect=lambda *args, **kwargs: sys.exit(0),  # noqa: ARG005
    )

    with EnvVars({AppEnvVars.NO_DYNAMIC_DEPS: "1"}):
        result = dda("inv", "foo")

    result.check(exit_code=0)

    assert exit_with.call_args_list == [
        mock.call(
            [
                sys.executable,
                "-m",
                "invoke",
                "foo",
            ],
        )
    ]
