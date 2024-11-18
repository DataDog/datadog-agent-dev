# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import pathlib
import sys
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner as __CliRunner
from platformdirs import user_cache_dir, user_data_dir

from deva.cli.application import Application
from deva.config.constants import AppEnvVars, ConfigEnvVars
from deva.config.file import ConfigFile
from deva.utils.ci import running_in_ci
from deva.utils.fs import Path, temp_directory
from deva.utils.platform import PLATFORM_ID
from deva.utils.process import EnvVars

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Generator


class CliRunner(__CliRunner):
    def __init__(self, command):
        super().__init__()
        self.__command = command

    def __call__(self, *args, **kwargs):
        # Exceptions should always be handled
        kwargs.setdefault("catch_exceptions", False)

        return self.invoke(self.__command, args, **kwargs)


class ConfigFileHelper(ConfigFile):
    def restore(self) -> None:
        self.save(None)


@pytest.fixture(scope="session")
def deva():
    from deva import cli

    return CliRunner(cli.deva)


@pytest.fixture
def temp_dir(tmp_path: pathlib.Path) -> Path:
    path = Path(tmp_path, "temp")
    path.mkdir()
    return path


@pytest.fixture(scope="session", autouse=True)
def isolation() -> Generator[Path, None, None]:
    with temp_directory() as d:
        data_dir = d / "data"
        data_dir.mkdir()
        cache_dir = d / "cache"
        cache_dir.mkdir()

        default_env_vars = {
            ConfigEnvVars.DATA: str(data_dir),
            ConfigEnvVars.CACHE: str(cache_dir),
            AppEnvVars.NO_COLOR: "1",
            "DEVA_SELF_TESTING": "true",
            "GIT_AUTHOR_NAME": "Foo Bar",
            "GIT_AUTHOR_EMAIL": "foo@bar.baz",
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
    config_file.data["storage"] = {"cache": str(cache_dir), "data": str(data_dir)}
    config_file.save()
    with EnvVars({ConfigEnvVars.CACHE: str(cache_dir), ConfigEnvVars.DATA: str(data_dir)}):
        yield


@pytest.fixture
def app(config_file: ConfigFile) -> Application:
    return Application(terminator=sys.exit, config_file=config_file, enable_color=False, interactive=False)


@pytest.fixture(scope="session")
def default_data_dir() -> Path:
    return Path(user_data_dir("deva", appauthor=False))


@pytest.fixture(scope="session")
def default_cache_dir() -> Path:
    return Path(user_cache_dir("deva", appauthor=False))


def pytest_runtest_setup(item):
    for marker in item.iter_markers():
        if marker.name == "requires_ci" and not running_in_ci():  # no cov
            pytest.skip("Not running in CI")

        if marker.name == "requires_windows" and PLATFORM_ID != "windows":
            pytest.skip("Not running on Windows")

        if marker.name == "requires_macos" and PLATFORM_ID != "macos":
            pytest.skip("Not running on macOS")

        if marker.name == "requires_linux" and PLATFORM_ID != "linux":
            pytest.skip("Not running on Linux")

        if marker.name == "requires_unix" and PLATFORM_ID == "windows":
            pytest.skip("Not running on a Linux-based platform")


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_ci: Tests intended for CI environments")
    config.addinivalue_line("markers", "requires_windows: Tests intended for Windows operating systems")
    config.addinivalue_line("markers", "requires_macos: Tests intended for macOS operating systems")
    config.addinivalue_line("markers", "requires_linux: Tests intended for Linux operating systems")
    config.addinivalue_line("markers", "requires_unix: Tests intended for Linux-based operating systems")

    config.getini("norecursedirs").remove("build")  # /tests/cli/build
