# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess
import sys
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

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Creating virtual environment
        Synchronizing dependencies
        """
    )

    expected_path = str(uv_on_path.with_stem(f"{uv_on_path.stem}-{uv_on_path.id}"))
    assert subprocess_run.call_args_list == [
        mock.call(
            [
                expected_path,
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
                expected_path,
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

    assert result.exit_code == 0, result.output
    assert not result.output

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

    assert result.exit_code == 0, result.output
    assert not result.output

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
