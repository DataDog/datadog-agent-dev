# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

import msgspec
import pytest

from dda.env.dev.interface import DeveloperEnvironmentConfig, DeveloperEnvironmentInterface
from dda.env.models import EnvironmentState, EnvironmentStatus

if TYPE_CHECKING:
    from dda.utils.editors.interface import EditorInterface

pytestmark = [pytest.mark.usefixtures("private_storage")]


class Container(DeveloperEnvironmentInterface):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def remove(self) -> None: ...

    def status(self) -> EnvironmentStatus:
        return EnvironmentStatus(state=EnvironmentState.UNKNOWN)

    def launch_shell(self, *, repo: str | None = None) -> NoReturn: ...

    def code(self, *, editor: EditorInterface, repo: str | None = None) -> None: ...

    def run_command(self, command: list[str], *, repo: str | None = None) -> None: ...


def test_storage_dirs(app, tmp_path):
    container = Container(app=app, name="test", instance="default")

    assert container.storage_dirs.cache == tmp_path / "cache" / "env" / "dev" / "test" / "default"
    assert container.storage_dirs.data == tmp_path / "data" / "env" / "dev" / "test" / "default"


class TestConfig:
    def test_default_config(self, app):
        container = Container(app=app, name="test", instance="default")

        assert msgspec.to_builtins(container.config) == {
            "clone": False,
            "repos": ["datadog-agent"],
        }

    def test_save(self, app):
        config = DeveloperEnvironmentConfig(repos=["foo", "bar"])
        container = Container(app=app, name="test", instance="default", config=config)
        container.save_config()

        container = Container(app=app, name="test", instance="default")
        assert container.config.repos == ["foo", "bar"]

    def test_remove(self, app):
        config = DeveloperEnvironmentConfig(repos=["foo", "bar"])
        container = Container(app=app, name="test", instance="default", config=config)
        container.save_config()

        container = Container(app=app, name="test", instance="default")
        assert container.config.repos == ["foo", "bar"]

        container = Container(app=app, name="test", instance="default")
        container.remove_config()
        assert container.config.repos == ["datadog-agent"]
