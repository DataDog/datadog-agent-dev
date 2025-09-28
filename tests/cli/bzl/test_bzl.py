# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess

from dda.tools.bazel import get_download_url
from dda.utils.process import EnvVars


def test_default_download(dda, helpers, isolation, mocker):
    args = ["build", "//..."]
    mocker.patch("dda.cli.base._get_argv", return_value=["dda", "bzl", *args])
    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")
    subprocess_runner = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0))

    with EnvVars(exclude=["PATH"]):
        result = dda("bzl", *args)

    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            Downloading Bazelisk
            """
        ),
    )

    internal_bazel_path = isolation.joinpath("cache", "tools", "bazel", "bazelisk").as_exe()
    downloader.assert_called_once_with(
        get_download_url(),
        path=internal_bazel_path,
    )
    subprocess_runner.assert_called_once_with([str(internal_bazel_path), *args])


def test_default_exists(dda, helpers, temp_dir, mocker):
    external_bazel_path = temp_dir.joinpath("bazel").as_exe()
    helpers.create_binary(external_bazel_path)

    args = ["build", "//..."]
    mocker.patch("dda.cli.base._get_argv", return_value=["dda", "bzl", *args])
    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")
    subprocess_runner = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0))

    with EnvVars({"PATH": str(temp_dir)}):
        result = dda("bzl", *args)

    result.check(exit_code=0)

    downloader.assert_not_called()
    subprocess_runner.assert_called_once_with([str(external_bazel_path), *args])


def test_config_force_managed(dda, helpers, isolation, config_file, temp_dir, mocker):
    config_file.data["tools"]["bazel"]["managed"] = True
    config_file.save()

    external_bazel_path = temp_dir.joinpath("bazel").as_exe()
    helpers.create_binary(external_bazel_path)

    args = ["build", "//..."]
    mocker.patch("dda.cli.base._get_argv", return_value=["dda", "bzl", *args])
    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")
    subprocess_runner = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0))

    with EnvVars({"PATH": str(temp_dir)}):
        result = dda("bzl", *args)

    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            Downloading Bazelisk
            """
        ),
    )

    internal_bazel_path = isolation.joinpath("cache", "tools", "bazel", "bazelisk").as_exe()
    downloader.assert_called_once_with(
        get_download_url(),
        path=internal_bazel_path,
    )
    subprocess_runner.assert_called_once_with([str(internal_bazel_path), *args])


def test_config_force_unmanaged(dda, helpers, config_file, mocker):
    config_file.data["tools"]["bazel"]["managed"] = False
    config_file.save()

    args = ["build", "//..."]
    mocker.patch("dda.cli.base._get_argv", return_value=["dda", "bzl", *args])
    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")

    with EnvVars(exclude=["PATH"]):
        result = dda("bzl", *args)

    result.check(
        exit_code=1,
        output=helpers.dedent(
            """
            Executable `bazel` not found: ['bazel', 'build', '//...']
            """
        ),
    )

    downloader.assert_not_called()


def test_arg_interception(dda, config_file, mocker):
    config_file.data["tools"]["bazel"]["managed"] = False
    config_file.save()

    args = ["build", "--", "//..."]
    mocker.patch("dda.cli.base._get_argv", return_value=["dda", "bzl", *args])
    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")

    with EnvVars(exclude=["PATH"]):
        result = dda("bzl", *args)

    result.check_exit_code(exit_code=1)
    assert result.output.startswith("Executable `bazel` not found: ['bazel', 'build', '--target_pattern_file', '")

    downloader.assert_not_called()
