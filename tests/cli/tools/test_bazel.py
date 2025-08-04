# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.tools.bazel import get_download_url
from dda.utils.process import EnvVars


def test_download(dda, helpers, config_file, isolation, mocker):
    config_file.data["tools"]["bazel"]["managed"] = True
    config_file.save()

    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")

    result = dda("tools", "bazel", "update")

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


def test_unmanaged(dda, helpers, config_file, temp_dir, mocker):
    config_file.data["tools"]["bazel"]["managed"] = False
    config_file.save()

    external_bazel_path = temp_dir.joinpath("bazel").as_exe()
    helpers.create_binary(external_bazel_path)

    downloader = mocker.patch("dda.utils.network.http.manager.HTTPClientManager.download")

    with EnvVars({"PATH": str(temp_dir)}):
        result = dda("tools", "bazel", "update")

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        f"""
        Bazel is not managed, using external version: {external_bazel_path}
        """
    )

    downloader.assert_not_called()
