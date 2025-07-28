# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import msgspec
import pytest

from dda.env.models import EnvironmentMetadata, EnvironmentNetworkMetadata, EnvironmentState, EnvironmentStatus
from dda.env.qa.interface import QAEnvironmentConfig, QAEnvironmentInterface

pytestmark = [pytest.mark.usefixtures("private_storage")]


class Container(QAEnvironmentInterface):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def restart(self) -> None: ...

    def remove(self) -> None: ...

    def sync_agent_config(self) -> None: ...

    def status(self) -> EnvironmentStatus:
        return EnvironmentStatus(state=EnvironmentState.UNKNOWN)

    def metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(network=EnvironmentNetworkMetadata(server="localhost"))

    def run_command(self, command: list[str]) -> None: ...


def test_storage_dirs(app, temp_dir):
    container = Container(app=app, name="test", instance="default")

    assert container.storage_dirs.cache == temp_dir / "cache" / "env" / "qa" / "test" / "default"
    assert container.storage_dirs.data == temp_dir / "data" / "env" / "qa" / "test" / "default"


class TestConfig:
    def test_default_config(self, app):
        container = Container(app=app, name="test", instance="default")

        assert msgspec.to_builtins(container.config) == {
            "env": {},
            "e2e": False,
        }

    def test_save(self, app):
        config = QAEnvironmentConfig(env={"foo": "bar"})
        container = Container(app=app, name="test", instance="default", config=config)
        container.save_state()

        container = Container(app=app, name="test", instance="default")
        assert container.config.env == {"foo": "bar"}

    def test_remove(self, app):
        config = QAEnvironmentConfig(env={"foo": "bar"})
        container = Container(app=app, name="test", instance="default", config=config)
        container.save_state()

        container = Container(app=app, name="test", instance="default")
        assert container.config.env == {"foo": "bar"}

        container = Container(app=app, name="test", instance="default")
        container.remove_state()
        assert container.config.env == {}
