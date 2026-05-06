# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import dda.utils.container.volumes as volumes

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.utils.fs import Path


class TestDockerVolumeHelpers:
    def test_volume_exists_true(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "capture", return_value="myvolume\n")
        assert app.tools.docker.volume_exists("myvolume")

    def test_volume_exists_false_empty(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "capture", return_value="")
        assert not app.tools.docker.volume_exists("myvolume")

    def test_volume_exists_no_partial_match(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "capture", return_value="myvolume-extra\n")
        assert not app.tools.docker.volume_exists("myvolume")

    def test_volume_list_empty(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "capture", return_value="")
        assert app.tools.docker.volume_list() == []

    def test_volume_list(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "capture", return_value="vol-a\nvol-b\n")
        assert app.tools.docker.volume_list() == ["vol-a", "vol-b"]


class TestListWithPrefix:
    def test_empty(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "volume_list", return_value=[])
        assert volumes.list_with_prefix(app, "devenv-foo-") == []

    def test_filters_by_prefix(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "volume_list", return_value=[
            "devenv-foo-org-repo",
            "devenv-bar-org-repo",
            "devenv-foo-org-other",
        ])
        assert volumes.list_with_prefix(app, "devenv-foo-") == [
            "devenv-foo-org-repo",
            "devenv-foo-org-other",
        ]

    def test_no_match(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "volume_list", return_value=["devenv-bar-x"])
        assert volumes.list_with_prefix(app, "devenv-foo-") == []


class TestExec:
    def test_no_mounts(self, app: Application, mocker) -> None:
        wait = mocker.patch.object(app.tools.docker, "wait")
        volumes.exec(app, image="alpine", command=["ls"])
        wait.assert_called_once_with(["run", "--rm", "alpine", "ls"])

    def test_with_volume(self, app: Application, mocker) -> None:
        wait = mocker.patch.object(app.tools.docker, "wait")
        volumes.exec(app, image="alpine", command=["ls"], volumes={"my-vol": "/data"})
        wait.assert_called_once_with(
            ["run", "--rm", "--mount", "type=volume,src=my-vol,dst=/data", "alpine", "ls"]
        )

    def test_with_bind_mount(self, app: Application, tmp_path: Path, mocker) -> None:
        from dda.utils.fs import Path as DdaPath

        wait = mocker.patch.object(app.tools.docker, "wait")
        host = DdaPath(tmp_path)
        volumes.exec(app, image="alpine", command=["ls"], bind_mounts={host: "/work"})
        wait.assert_called_once_with(
            ["run", "--rm", "--mount", f"type=bind,src={host},dst=/work", "alpine", "ls"]
        )

    def test_capture_mode(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "capture", return_value="output\n")
        result = volumes.exec(app, image="alpine", command=["ls"], capture=True)
        assert result == "output\n"

    def test_no_capture_returns_none(self, app: Application, mocker) -> None:
        mocker.patch.object(app.tools.docker, "wait")
        result = volumes.exec(app, image="alpine", command=["ls"])
        assert result is None
