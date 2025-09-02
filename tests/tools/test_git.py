# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import random
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from dda.tools.git import Git
from dda.utils.fs import Path
from dda.utils.git.commit import Commit
from dda.utils.git.sha1hash import SHA1Hash

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from dda.cli.application import Application


# Initialize a dummy repo in a temporary directory for the tests to use
@pytest.fixture
def temp_repo(app: Application, temp_dir: Path, set_commiter_details: None) -> Generator[Path, None, None]:  # noqa: ARG001
    git: Git = app.tools.git
    repo_path = temp_dir / "dummy-repo"
    repo_path.mkdir()  # Don't do exist_ok, the directory should not exist
    with repo_path.as_cwd():
        git.run(["init", "--initial-branch", "main"])
    yield repo_path
    # Cleanup
    import shutil

    shutil.rmtree(repo_path)


@pytest.fixture
def set_commiter_details(app: Application) -> Generator[None, None, None]:
    # The cleanup here is very important as it affects the global git config
    old_env_author = os.environ.pop(Git.AUTHOR_NAME_ENV_VAR, default=None)
    old_env_email = os.environ.pop(Git.AUTHOR_EMAIL_ENV_VAR, default=None)
    old_author_name = app.tools.git.capture(["config", "--global", "--get", "user.name"], check=False)
    old_author_email = app.tools.git.capture(["config", "--global", "--get", "user.email"], check=False)
    app.tools.git.run(["config", "--global", "user.name", "Test Runner"])
    app.tools.git.run(["config", "--global", "user.email", "test.runner@example.com"])
    yield
    app.tools.git.run(["config", "--global", "--unset", "user.name"])
    app.tools.git.run(["config", "--global", "--unset", "user.email"])
    if old_author_name:
        app.tools.git.run(["config", "--global", "user.name", old_author_name])
    if old_author_email:
        app.tools.git.run(["config", "--global", "user.email", old_author_email])
    if old_env_author:
        os.environ[Git.AUTHOR_NAME_ENV_VAR] = old_env_author
    if old_env_email:
        os.environ[Git.AUTHOR_EMAIL_ENV_VAR] = old_env_email


# Create a dummy file in the repository - uses the previously initialized dummy repo and the "fixture factory" pattern
# Commiter details are set automatically be the env vars in conftest.py
@pytest.fixture(name="create_commit_dummy_file")
def fixt_create_commit_dummy_file(
    app: Application,
    temp_repo: Path,
) -> Callable[[Path | str, str, str], None]:
    git: Git = app.tools.git

    def _create_commit_dummy_file(location: Path | str, content: str, commit_message: str) -> None:
        if isinstance(location, str):
            location = Path(location)

        if location.is_absolute():
            try:
                location = location.relative_to(temp_repo)
            except ValueError as e:
                msg = "Location must be a relative path to the temporary directory"
                raise ValueError(msg) from e

        with temp_repo.as_cwd():
            location.write_text(content)
            git.run(["add", str(location)])
            git.run(["commit", "-m", f'"{commit_message}"'])

    return _create_commit_dummy_file


def test_basic(
    app: Application, temp_repo: Path, create_commit_dummy_file: Callable[[Path | str, str, str], None]
) -> None:
    with temp_repo.as_cwd():
        assert app.tools.git.run(["status"]) == 0
        random_key = random.randint(1, 1000000)
        create_commit_dummy_file("testfile.txt", "test", f"Initial commit: {random_key}")
        assert f"Initial commit: {random_key}" in app.tools.git.capture(["log", "-1", "--oneline"])


def clear_cached_config(app: Application) -> None:
    if hasattr(app.config_file, "model"):
        del app.config_file.model

    if hasattr(app, "config"):
        del app.config


@pytest.fixture
def reset_user_config(app: Application) -> None:
    # Modify the underlying config data and clear the cached model
    app.config_file.data["user"]["name"] = ""
    app.config_file.data["user"]["email"] = ""

    # Clear the cached properties so they get reconstructed with the new data
    clear_cached_config(app)

    # These are set by conftest.py, so we need to clean them up to make sure they don't interfere
    os.environ.pop("GIT_AUTHOR_NAME", None)
    os.environ.pop("GIT_AUTHOR_EMAIL", None)


def test_author_details(app: Application, reset_user_config: None, set_commiter_details: None) -> None:  # noqa: ARG001
    # Test 1: Test author details coming from global git config - lowest priority
    # The set_commiter_details fixture ensures the global git config is set to known values
    assert app.tools.git.get_author_name() == "Test Runner"
    assert app.tools.git.get_author_email() == "test.runner@example.com"

    # Test 2: Test author details coming from environment variables - second priority
    os.environ[Git.AUTHOR_NAME_ENV_VAR] = "Jane Smith"
    os.environ[Git.AUTHOR_EMAIL_ENV_VAR] = "jane.smith@example.com"
    assert app.tools.git.get_author_name() == "Jane Smith"
    assert app.tools.git.get_author_email() == "jane.smith@example.com"

    # Test 3: Test author details coming from dda config - highest priority
    app.config_file.data["user"]["name"] = "John Doe"
    app.config_file.data["user"]["email"] = "john.doe@example.com"

    # Clear the cached properties so they get reconstructed with the new data
    clear_cached_config(app)
    assert app.tools.git.get_author_name() == "John Doe"
    assert app.tools.git.get_author_email() == "john.doe@example.com"


@pytest.fixture
def temp_repo_with_remote(app: Application, temp_repo: Path) -> Path:
    with temp_repo.as_cwd():
        app.tools.git.run(["remote", "add", "origin", "https://github.com/foo/bar"])
    return temp_repo


def test_get_remote_details(app: Application, temp_repo_with_remote: Path) -> None:
    with temp_repo_with_remote.as_cwd():
        assert app.tools.git.get_remote_details() == ("foo", "bar", "https://github.com/foo/bar")


def test_get_head_commit(
    app: Application, temp_repo_with_remote: Path, create_commit_dummy_file: Callable[[Path | str, str, str], None]
) -> None:
    with temp_repo_with_remote.as_cwd():
        create_commit_dummy_file("hello.txt", "world", "Brand-new commit")
        sha1 = app.tools.git.capture(["rev-parse", "HEAD"]).strip()

        assert app.tools.git.get_head_commit() == Commit(org="foo", repo="bar", sha1=SHA1Hash(sha1))


def test_get_commit_details(
    app: Application, temp_repo: Path, create_commit_dummy_file: Callable[[Path | str, str, str], None]
) -> None:
    with temp_repo.as_cwd():
        create_commit_dummy_file("dummy", "dummy content", "Initial commit")
        parent_sha1 = app.tools.git.capture(["rev-parse", "HEAD"]).strip()

        random_key = random.randint(1, 1000000)
        create_commit_dummy_file("hello.txt", "world", f"Brand-new commit: {random_key}")
        sha1 = app.tools.git.capture(["rev-parse", "HEAD"]).strip()
        commit_time = datetime.fromisoformat(app.tools.git.capture(["show", "-s", "--format=%cI", sha1]).strip())

        details = app.tools.git.get_commit_details(SHA1Hash(sha1))
        assert details.author_name == "Test Runner"
        assert details.author_email == "test.runner@example.com"
        assert details.datetime == commit_time
        assert details.message == f"Brand-new commit: {random_key}"
        assert details.parent_shas == [SHA1Hash(parent_sha1)]
