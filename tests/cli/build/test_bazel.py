# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess

from dda.tools.bazel import get_download_url
from dda.utils.process import EnvVars


def test_default_download(dda, helpers, isolation, mocker):
    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")
    subprocess_runner = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0))

    with EnvVars(exclude=["PATH"]):
        result = dda("build", "bazel", "build", "//...")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Downloading Bazelisk
        """
    )

    internal_bazel_path = isolation.joinpath("cache", "tools", "bazel", "bazelisk").as_exe()
    downloader.assert_called_once_with(
        get_download_url(),
        path=internal_bazel_path,
    )
    subprocess_runner.assert_called_once_with([str(internal_bazel_path), "build", "//..."])


def test_default_exists(dda, helpers, temp_dir, mocker):
    external_bazel_path = temp_dir.joinpath("bazel").as_exe()
    helpers.create_binary(external_bazel_path)

    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")
    subprocess_runner = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0))

    with EnvVars({"PATH": str(temp_dir)}):
        result = dda("build", "bazel", "build", "//...")

    assert result.exit_code == 0, result.output
    assert not result.output

    downloader.assert_not_called()
    subprocess_runner.assert_called_once_with([str(external_bazel_path), "build", "//..."])


def test_config_force_managed(dda, helpers, isolation, config_file, temp_dir, mocker):
    config_file.data["tools"]["bazel"]["managed"] = True
    config_file.save()

    external_bazel_path = temp_dir.joinpath("bazel").as_exe()
    helpers.create_binary(external_bazel_path)

    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")
    subprocess_runner = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0))

    with EnvVars({"PATH": str(temp_dir)}):
        result = dda("build", "bazel", "build", "//...")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Downloading Bazelisk
        """
    )

    internal_bazel_path = isolation.joinpath("cache", "tools", "bazel", "bazelisk").as_exe()
    downloader.assert_called_once_with(
        get_download_url(),
        path=internal_bazel_path,
    )
    subprocess_runner.assert_called_once_with([str(internal_bazel_path), "build", "//..."])


def test_config_force_unmanaged(dda, helpers, config_file, mocker):
    config_file.data["tools"]["bazel"]["managed"] = False
    config_file.save()

    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")

    with EnvVars(exclude=["PATH"]):
        result = dda("build", "bazel", "build", "//...")

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        """
        Executable `bazel` not found: ['bazel', 'build', '//...']
        """
    )

    downloader.assert_not_called()
