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
from dda.utils.git.commit import Commit, SHA1Hash
from tests.tools.conftest import clear_cached_config

if TYPE_CHECKING:
    from collections.abc import Callable

    from dda.cli.application import Application
    from dda.utils.fs import Path
    from dda.utils.git.changeset import ChangeSet


def test_basic(
    app: Application, temp_repo: Path, create_commit_dummy_file: Callable[[Path | str, str, str], None]
) -> None:
    with temp_repo.as_cwd():
        assert app.tools.git.run(["status"]) == 0
        random_key = random.randint(1, 1000000)
        create_commit_dummy_file("testfile.txt", "test", f"Initial commit: {random_key}")
        assert f"Initial commit: {random_key}" in app.tools.git.capture(["log", "-1", "--oneline"])


def test_author_details(app: Application, reset_user_config: None, set_commiter_details: None) -> None:  # noqa: ARG001
    # Test 1: Test author details coming from global git config - lowest priority
    # The set_commiter_details fixture ensures the global git config is set to known values
    clear_cached_config(app)
    assert app.tools.git.author_name == "Test Runner"
    assert app.tools.git.author_email == "test.runner@example.com"

    # Test 2: Test author details coming from environment variables - second priority
    clear_cached_config(app)
    os.environ[Git.AUTHOR_NAME_ENV_VAR] = "Jane Smith"
    os.environ[Git.AUTHOR_EMAIL_ENV_VAR] = "jane.smith@example.com"
    assert app.tools.git.author_name == "Jane Smith"
    assert app.tools.git.author_email == "jane.smith@example.com"

    # Test 3: Test author details coming from dda config - highest priority
    app.config_file.data["user"]["name"] = "John Doe"
    app.config_file.data["user"]["email"] = "john.doe@example.com"

    # Clear the cached properties so they get reconstructed with the new data
    clear_cached_config(app)
    assert app.tools.git.author_name == "John Doe"
    assert app.tools.git.author_email == "john.doe@example.com"


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


# These tests are quite slow (the setup fixtures are quite heavy), and mostly replicated in the utils/git/test_changeset.py tests
# Thus we only run them in CI
@pytest.mark.requires_ci
def test_get_commit_changes(app: Application, repo_setup: tuple[Path, ChangeSet]) -> None:
    git: Git = app.tools.git
    temp_repo, expected_changeset = repo_setup
    with temp_repo.as_cwd():
        changeset = git.get_commit_changes(SHA1Hash(git.capture(["rev-parse", "HEAD"]).strip()))
        assert changeset.keys() == expected_changeset.keys()
        for file in changeset:
            seen, expected = changeset[file], expected_changeset[file]
            assert seen.file == expected.file
            assert seen.type == expected.type
            assert seen.patch == expected.patch


@pytest.mark.requires_ci
def test_get_working_tree_changes(app: Application, repo_setup_working_tree: tuple[Path, ChangeSet]) -> None:
    git: Git = app.tools.git
    temp_repo, expected_changeset = repo_setup_working_tree
    with temp_repo.as_cwd():
        changeset = git.get_working_tree_changes()
        assert changeset.keys() == expected_changeset.keys()
        for file in changeset:
            seen, expected = changeset[file], expected_changeset[file]
            assert seen.file == expected.file
            assert seen.type == expected.type
            assert seen.patch == expected.patch
