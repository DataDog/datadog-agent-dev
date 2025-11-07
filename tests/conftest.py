# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
import time
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from click import testing as click_testing
from platformdirs import user_cache_dir, user_data_dir

from dda.cli.application import Application
from dda.config.constants import AppEnvVars, ConfigEnvVars
from dda.config.file import ConfigFile
from dda.utils.ci import running_in_ci
from dda.utils.fs import Path, temp_directory
from dda.utils.git.constants import GitEnvVars
from dda.utils.platform import PLATFORM_ID, which
from dda.utils.process import EnvVars

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Generator
    from uuid import UUID

    from dda.config.model.tools import GitAuthorConfig


class Result:
    def __init__(self, result: click_testing.Result):
        self.__result = result

    def check(
        self,
        *,
        exit_code: int,
        stdout: str = "",
        stdout_json: dict[str, Any] | None = None,
        stderr: str | None = None,
        stderr_json: dict[str, Any] | None = None,
        output: str = "",
    ) -> None:
        self.check_exit_code(exit_code)

        if stdout_json is not None:
            assert json.loads(self.__result.stdout) == stdout_json
        else:
            assert self.__result.stdout == stdout

        if stderr_json is not None:
            assert json.loads(self.__result.stderr) == stderr_json
        elif stderr is not None:
            if stdout_json is None:
                msg = "Assert on the combined `output` when not expecting JSON"
                raise ValueError(msg)

            assert self.__result.stderr == stderr
        elif stdout_json is not None:
            assert json.loads(self.__result.output) == stdout_json
        else:
            assert self.__result.output == (output or stdout)

    def check_exit_code(self, exit_code: int) -> None:
        assert self.__result.exit_code == exit_code, self.__result.output

    @property
    def stdout(self) -> str:
        return self.__result.stdout

    @property
    def output(self) -> str:
        return self.__result.output


class CliRunner(click_testing.CliRunner):
    def __init__(self, command):
        super().__init__()
        self.__command = command

    def __call__(self, *args, **kwargs):
        # Exceptions should always be handled
        kwargs.setdefault("catch_exceptions", False)

        return Result(self.invoke(self.__command, args, **kwargs))


class ConfigFileHelper(ConfigFile):
    def restore(self) -> None:
        self.save(None)


@pytest.fixture(scope="session")
def dda():
    from dda import cli

    return CliRunner(cli.dda)


@pytest.fixture
def temp_dir(tmp_path: pathlib.Path) -> Path:
    return Path(tmp_path)


@pytest.fixture(scope="session", autouse=True)
def isolation(default_git_author: GitAuthorConfig) -> Generator[Path, None, None]:
    with temp_directory() as d:
        data_dir = d / "data"
        data_dir.mkdir()
        cache_dir = d / "cache"
        cache_dir.mkdir()

        # Disable telemetry
        dissent_file = cache_dir / "telemetry" / "dissent"
        dissent_file.parent.ensure_dir()
        dissent_file.touch()

        # Disable update checker
        last_update_check_file = cache_dir / "last_update_check"
        last_update_check_file.write_text(str(time.time()), encoding="utf-8")

        default_env_vars = {
            ConfigEnvVars.DATA: str(data_dir),
            ConfigEnvVars.CACHE: str(cache_dir),
            AppEnvVars.NO_COLOR: "1",
            "PYAPP": "1",
            "DDA_SELF_TESTING": "true",
            GitEnvVars.AUTHOR_NAME: default_git_author.name,
            GitEnvVars.AUTHOR_EMAIL: default_git_author.email,
            "COLUMNS": "80",
            "LINES": "24",
        }
        with d.as_cwd(), EnvVars(default_env_vars):
            os.environ.pop(AppEnvVars.FORCE_COLOR, None)
            yield d


@pytest.fixture(scope="session")
def helpers():
    # https://docs.pytest.org/en/latest/writing_plugins.html#assertion-rewriting
    pytest.register_assert_rewrite("tests.helpers.api")

    from .helpers import api

    return api


@pytest.fixture(autouse=True)
def config_file(tmp_path: pathlib.Path) -> ConfigFile:
    path = os.path.join(tmp_path, "config.toml")
    os.environ[ConfigEnvVars.CONFIG] = path
    config = ConfigFile(path)
    config.restore()
    return config


@pytest.fixture
def private_storage(config_file: ConfigFile) -> Generator[None, None, None]:
    cache_dir = config_file.path.parent / "cache"
    cache_dir.mkdir()
    data_dir = config_file.path.parent / "data"
    data_dir.mkdir()

    # Disable telemetry
    dissent_file = cache_dir / "telemetry" / "dissent"
    dissent_file.parent.ensure_dir()
    dissent_file.touch()

    # Disable update checker
    last_update_check_file = cache_dir / "last_update_check"
    last_update_check_file.write_text(str(time.time()), encoding="utf-8")

    config_file.data["storage"] = {"cache": str(cache_dir), "data": str(data_dir)}
    config_file.save()
    with EnvVars({ConfigEnvVars.CACHE: str(cache_dir), ConfigEnvVars.DATA: str(data_dir)}):
        yield


@pytest.fixture
def app(config_file: ConfigFile) -> Application:
    return Application(terminator=sys.exit, config_file=config_file, enable_color=False, interactive=False)


@pytest.fixture(scope="session")
def default_data_dir() -> Path:
    return Path(user_data_dir("dda", appauthor=False))


@pytest.fixture(scope="session")
def default_cache_dir() -> Path:
    return Path(user_cache_dir("dda", appauthor=False))


@pytest.fixture(scope="session")
def default_git_author() -> GitAuthorConfig:
    from dda.config.model.tools import GitAuthorConfig

    return GitAuthorConfig(name="Foo Bar", email="foo@bar.baz")


@pytest.fixture(scope="session")
def default_gopath() -> Path:
    return Path(Path.home() / "go")


@pytest.fixture(scope="session")
def default_gocache() -> Path:
    return Path(Path.home() / ".cache/go-build")


@pytest.fixture(scope="session")
def uv_on_path() -> Path:
    return Path(shutil.which("uv"))


@pytest.fixture(scope="session")
def bazel_on_path() -> Path:
    return Path(which("bazel"))


@pytest.fixture(scope="session", autouse=True)
def machine_id() -> Generator[UUID, None, None]:
    # The logic on macOS requires a subprocess call which interferes with tests expecting
    # such calls being in a certain order with specific output
    from uuid import UUID

    with patch("dda.utils.platform.get_machine_id", return_value=UUID("12345678-1234-5678-1234-567812345678")) as mock:
        yield mock.return_value


def pytest_runtest_setup(item):
    for marker in item.iter_markers():
        if marker.name == "requires_ci" and not running_in_ci():  # no cov
            pytest.skip("Not running in CI")

        if marker.name == "requires_windows" and PLATFORM_ID != "windows":
            pytest.skip("Not running on Windows")

        if marker.name == "skip_windows" and PLATFORM_ID == "windows":
            pytest.skip("Test should be skipped on Windows")

        if marker.name == "requires_macos" and PLATFORM_ID != "macos":
            pytest.skip("Not running on macOS")

        if marker.name == "skip_macos" and PLATFORM_ID == "macos":
            pytest.skip("Test should be skipped on macOS")

        if marker.name == "requires_linux" and PLATFORM_ID != "linux":
            pytest.skip("Not running on Linux")

        if marker.name == "skip_linux" and PLATFORM_ID == "linux":
            pytest.skip("Test should be skipped on Linux")

        if marker.name == "requires_unix" and PLATFORM_ID not in {"linux", "macos"}:
            pytest.skip("Not running on a Unix-based platform")

        if marker.name == "skip_unix" and PLATFORM_ID in {"linux", "macos"}:
            pytest.skip("Test should be skipped on Unix-based platforms")


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_ci: Tests intended for CI environments")
    config.addinivalue_line("markers", "requires_windows: Tests intended for Windows operating systems")
    config.addinivalue_line("markers", "skip_windows: Tests should be skipped on Windows operating systems")
    config.addinivalue_line("markers", "requires_macos: Tests intended for macOS operating systems")
    config.addinivalue_line("markers", "skip_macos: Tests should be skipped on macOS operating systems")
    config.addinivalue_line("markers", "requires_linux: Tests intended for Linux operating systems")
    config.addinivalue_line("markers", "skip_linux: Tests should be skipped on Linux operating systems")
    config.addinivalue_line("markers", "requires_unix: Tests intended for Linux-based operating systems")
    config.addinivalue_line("markers", "skip_unix: Tests should be skipped on Unix-based operating systems")

    config.getini("norecursedirs").remove("build")  # /tests/cli/build
