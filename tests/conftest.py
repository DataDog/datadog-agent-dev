# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import time
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner as __CliRunner
from platformdirs import user_cache_dir, user_data_dir

from dda.cli.application import Application
from dda.config.constants import AppEnvVars, ConfigEnvVars
from dda.config.file import ConfigFile
from dda.utils.ci import running_in_ci
from dda.utils.fs import Path, temp_directory
from dda.utils.git.constants import GitAuthorEnvVars
from dda.utils.platform import PLATFORM_ID
from dda.utils.process import EnvVars

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
def dda():
    from dda import cli

    return CliRunner(cli.dda)


@pytest.fixture
def temp_dir(tmp_path: pathlib.Path) -> Path:
    return Path(tmp_path)


@pytest.fixture(scope="session", autouse=True)
def isolation() -> Generator[Path, None, None]:
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
            GitAuthorEnvVars.NAME: "Foo Bar",
            GitAuthorEnvVars.EMAIL: "foo@bar.baz",
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
def uv_on_path() -> Path:
    return Path(shutil.which("uv"))


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
