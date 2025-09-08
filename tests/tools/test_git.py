# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import random
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest

from dda.utils.fs import Path
from dda.utils.git.changeset import ChangeSet, ChangeType, FileChanges
from dda.utils.git.commit import Commit
from tests.tools.conftest import REPO_TESTCASES, _load_changeset, clear_cached_config

if TYPE_CHECKING:
    from collections.abc import Callable

    from dda.cli.application import Application
    from dda.tools.git import Git


def assert_changesets_equal(actual: ChangeSet, expected: ChangeSet) -> None:
    """
    Assert that two ChangeSet objects are equal by comparing their keys and
    each FileChanges object's file, type, and patch attributes.

    Args:
        actual: The actual ChangeSet to compare
        expected: The expected ChangeSet to compare against
    """
    assert actual.keys() == expected.keys()
    for file in actual:
        seen, expected_change = actual[file], expected[file]
        assert seen.file == expected_change.file
        assert seen.type == expected_change.type
        assert seen.patch == expected_change.patch


def test_basic(
    app: Application, temp_repo: Path, create_commit_dummy_file: Callable[[Path | str, str, str], None]
) -> None:
    with temp_repo.as_cwd():
        assert app.tools.git.run(["status"]) == 0
        random_key = random.randint(1, 1000000)
        create_commit_dummy_file("testfile.txt", "test", f"Initial commit: {random_key}")
        assert f"Initial commit: {random_key}" in app.tools.git.capture(["log", "-1", "--oneline"])


def test_author_details(app: Application, set_git_author: None) -> None:  # noqa: ARG001
    clear_cached_config(app)
    assert app.tools.git.author_name == "Test Runner"
    assert app.tools.git.author_email == "test.runner@example.com"


def test_get_remote_details(app: Application, temp_repo_with_remote: Path) -> None:
    with temp_repo_with_remote.as_cwd():
        assert app.tools.git.get_remote_details() == ("foo", "bar", "https://github.com/foo/bar")


def test_get_head_commit(
    app: Application, temp_repo_with_remote: Path, create_commit_dummy_file: Callable[[Path | str, str, str], None]
) -> None:
    with temp_repo_with_remote.as_cwd():
        create_commit_dummy_file("hello.txt", "world", "Brand-new commit")
        sha1 = app.tools.git.capture(["rev-parse", "HEAD"]).strip()

        assert app.tools.git.get_head_commit() == Commit(org="foo", repo="bar", sha1=sha1)


def test_get_commit_details(
    app: Application,
    temp_repo: Path,
    create_commit_dummy_file: Callable[[Path | str, str, str], None],
) -> None:
    with temp_repo.as_cwd():
        create_commit_dummy_file("dummy", "dummy content", "Initial commit")
        parent_sha1 = app.tools.git.capture(["rev-parse", "HEAD"]).strip()

        random_key = random.randint(1, 1000000)
        create_commit_dummy_file("hello.txt", "world", f"Brand-new commit: {random_key}")
        sha1 = app.tools.git.capture(["rev-parse", "HEAD"]).strip()
        commit_time = datetime.fromisoformat(app.tools.git.capture(["show", "-s", "--format=%cI", sha1]).strip())

        details = app.tools.git.get_commit_details(sha1)
        assert details.author_name == "Test Runner"
        assert details.author_email == "test.runner@example.com"
        assert details.datetime == commit_time
        assert details.message == f"Brand-new commit: {random_key}"
        assert details.parent_shas == [parent_sha1]


def test_capture_diff_lines(
    app: Application, temp_repo: Path, create_commit_dummy_file: Callable[[Path | str, str, str], None]
) -> None:
    with temp_repo.as_cwd():
        contents = "hello, world\n"
        # Need to make an initial commit to have a valid diff
        create_commit_dummy_file("dummy", "", "Initial commit")
        create_commit_dummy_file("hello.txt", contents, "New commit")
        diff_lines = app.tools.git._capture_diff_lines("HEAD^", "HEAD")  # noqa: SLF001
        expected_patterns = [
            "diff --git hello.txt hello.txt",
            "new file mode 100644",
            re.compile("index 0000000..[0-9a-f]{6}"),
            "--- /dev/null",
            "+++ hello.txt",
            "@@ -0,0 +1 @@",
            f"+{contents.strip()}",
        ]

        for line, pattern in zip(diff_lines, expected_patterns, strict=True):
            if isinstance(pattern, re.Pattern):
                assert pattern.match(line)
            else:
                assert line == pattern


@pytest.mark.parametrize("repo_testcase", REPO_TESTCASES)
def test_compare_refs(app: Application, mocker: Any, repo_testcase: str) -> None:
    testcase_dir = Path(__file__).parent / "fixtures" / "repo_states" / repo_testcase
    with open(testcase_dir / "diff_output.txt", encoding="utf-8") as f:
        diff_output = f.read()
    mocker.patch("dda.tools.git.Git._capture_diff_lines", return_value=diff_output.splitlines())
    result = app.tools.git._compare_refs("", "")  # noqa: SLF001
    expected_changeset = _load_changeset(testcase_dir / "expected_changeset.json")
    assert_changesets_equal(result, expected_changeset)


# These tests are quite slow (the setup fixtures are quite heavy), and mostly replicated in the utils/git/test_changeset.py tests
# Thus we only run them in CI
@pytest.mark.requires_ci
def test_get_commit_changes(app: Application, repo_setup: tuple[Path, ChangeSet]) -> None:
    git: Git = app.tools.git
    temp_repo, expected_changeset = repo_setup
    with temp_repo.as_cwd():
        changeset = git.get_commit_changes(git.capture(["rev-parse", "HEAD"]).strip())
        assert_changesets_equal(changeset, expected_changeset)


@pytest.mark.parametrize("repo_testcase", REPO_TESTCASES)
def test_get_changes_between_commits(app: Application, mocker: Any, repo_testcase: str) -> None:
    testcase_dir = Path(__file__).parent / "fixtures" / "repo_states" / repo_testcase
    expected_changeset = _load_changeset(testcase_dir / "expected_changeset.json")

    mocker.patch("dda.tools.git.Git._compare_refs", return_value=expected_changeset)
    commit1 = Commit(org="foo", repo="bar", sha1="a" * 40)
    commit2 = Commit(org="foo", repo="bar", sha1="b" * 40)
    result = app.tools.git.get_changes_between_commits(commit1.sha1, commit2.sha1)
    assert_changesets_equal(result, expected_changeset)


# @pytest.mark.requires_ci
def test_get_working_tree_changes(app: Application, repo_setup_working_tree: tuple[Path, ChangeSet]) -> None:
    git: Git = app.tools.git
    temp_repo, expected_changeset = repo_setup_working_tree
    with temp_repo.as_cwd():
        changeset = git.get_working_tree_changes()
        assert_changesets_equal(changeset, expected_changeset)


# TODO: Add a test for this - seems a bit complicated to test
def test_get_merge_base(app: Application) -> None:
    pass


@pytest.mark.parametrize("repo_testcase", REPO_TESTCASES)
def test_get_changes_with_base(app: Application, mocker: Any, repo_testcase: str) -> None:
    testcase_dir = Path(__file__).parent / "fixtures" / "repo_states" / repo_testcase
    expected_changeset = _load_changeset(testcase_dir / "expected_changeset.json")

    git: Git = app.tools.git
    base_commit = Commit(org="foo", repo="bar", sha1="a" * 40)
    head_commit = Commit(org="foo", repo="bar", sha1="b" * 40)

    # Mock the underlying functions
    mocker.patch("dda.tools.git.Git.get_head_commit", return_value=head_commit)
    mocker.patch("dda.utils.git.changeset.ChangeSet.generate_from_diff_output", return_value=expected_changeset)

    # Test without working tree changes
    changeset = git.get_changes_with_base(base_commit.sha1, include_working_tree=False)
    assert_changesets_equal(changeset, expected_changeset)

    # Test with working tree changes
    working_tree_changes = ChangeSet({
        Path("test.txt"): FileChanges(file=Path("test.txt"), type=ChangeType.ADDED, patch="@@ -0,0 +1 @@\n+test")
    })
    mocker.patch("dda.tools.git.Git.get_working_tree_changes", return_value=working_tree_changes)

    changeset_with_working_tree = git.get_changes_with_base(base_commit.sha1, include_working_tree=True)
    expected_changeset_with_working_tree = expected_changeset | ChangeSet.from_iter([
        FileChanges(file=Path("test.txt"), type=ChangeType.ADDED, patch="@@ -0,0 +1 @@\n+test")
    ])
    assert_changesets_equal(changeset_with_working_tree, expected_changeset_with_working_tree)
