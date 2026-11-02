# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

import msgspec
import pytest

from dda.env.dev.interface import (
    DeveloperEnvironmentConfig,
    DeveloperEnvironmentInterface,
    RepositorySpec,
    is_enterprise_github_owner,
)
from dda.env.models import EnvironmentState, EnvironmentStatus

if TYPE_CHECKING:
    from dda.utils.editors.interface import EditorInterface
    from dda.utils.fs import Path

pytestmark = [pytest.mark.usefixtures("private_storage")]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            "datadog-agent",
            RepositorySpec(owner="DataDog", name="datadog-agent", ref="", qualified=False),
            id="default owner",
        ),
        pytest.param(
            "ddoghq/repository@feature",
            RepositorySpec(owner="ddoghq", name="repository", ref="feature", qualified=True),
            id="qualified with ref",
        ),
        pytest.param(
            "ddoghq-sandbox/experiment",
            RepositorySpec(owner="ddoghq-sandbox", name="experiment", ref="", qualified=True),
            id="sandbox",
        ),
    ],
)
def test_repository_spec(value: str, expected: RepositorySpec) -> None:
    repository = RepositorySpec.parse(value)

    assert repository == expected
    assert repository.full_name == f"{expected.owner}/{expected.name}"
    assert repository.clone_name == (expected.full_name if expected.qualified else expected.name)


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "../repository",
        "/repository",
        "owner/",
        "owner/.",
        "owner/..",
        "owner/group/repository",
        r"owner\repository",
        "owner:repository",
        "owner/repository:destination",
        "owner/repository destination",
        "-owner/repository",
        "owner-/repository",
        "owner--name/repository",
        f"{'o' * 40}/repository",
        f"owner/{'r' * 101}",
    ],
)
def test_invalid_repository_spec(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid repository specification"):
        RepositorySpec.parse(value)


def test_repository_spec_accepts_github_name_limits() -> None:
    value = f"{'o' * 39}/{'r' * 100}"

    assert RepositorySpec.parse(value).full_name == value


@pytest.mark.parametrize("owner", ["DDOGHQ", "DDOGHQ-sandbox", "ddoghq-New-Org"])
def test_repository_spec_rejects_noncanonical_enterprise_owner(owner: str) -> None:
    with pytest.raises(ValueError, match="must use canonical lowercase casing"):
        RepositorySpec.parse(f"{owner}/repository")


@pytest.mark.parametrize(
    ("owner", "expected"),
    [("ddoghq", True), ("ddoghq-sandbox", True), ("ddoghq-new-org", True), ("ddoghqish", False), ("DataDog", False)],
)
def test_enterprise_github_owner(owner: str, *, expected: bool) -> None:
    assert is_enterprise_github_owner(owner) is expected


class Container(DeveloperEnvironmentInterface):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def remove(self) -> None: ...

    def status(self) -> EnvironmentStatus:
        return EnvironmentStatus(state=EnvironmentState.UNKNOWN)

    def launch_shell(self, *, repo: str | None = None) -> NoReturn: ...

    def code(self, *, editor: EditorInterface, repo: str | None = None) -> None: ...

    def run_command(self, command: list[str], *, repo: str | None = None) -> None: ...

    def export_path(
        self,
        source: str,
        destination: Path,
    ) -> None: ...

    def import_path(
        self,
        source: Path,
        destination: str,
    ) -> None: ...


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

    def test_owner_qualified_default_repository(self, app):
        config = DeveloperEnvironmentConfig(repos=["ddoghq/repository@feature"])
        container = Container(app=app, name="test", instance="default", config=config)

        assert container.default_repo == "repository"

    def test_remove(self, app):
        config = DeveloperEnvironmentConfig(repos=["foo", "bar"])
        container = Container(app=app, name="test", instance="default", config=config)
        container.save_config()

        container = Container(app=app, name="test", instance="default")
        assert container.config.repos == ["foo", "bar"]

        container = Container(app=app, name="test", instance="default")
        container.remove_config()
        assert container.config.repos == ["datadog-agent"]
