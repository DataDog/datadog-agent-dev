# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING

from dda.utils.fs import Path
from dda.utils.git.changeset import ChangedFile, ChangeSet, ChangeType
from dda.utils.git.commit import GitPersonDetails
from dda.utils.git.constants import GitEnvVars
from dda.utils.process import EnvVars

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.config.model.tools import GitAuthorConfig
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
        assert seen.path == expected_change.path
        assert seen.type == expected_change.type
        assert seen.patch == expected_change.patch


def test_basic(app: Application, temp_repo: Path) -> None:  # type: ignore[no-untyped-def]
    with temp_repo.as_cwd():
        app.tools.git.capture(["status"])
        random_key = random.randint(1, 1000000)
        with temp_repo.as_cwd():
            file = Path("testfile.txt")
            file.write_text("test")
            app.tools.git.capture(["add", str(file)])
            app.tools.git.capture(["commit", "-m", f"Initial commit: {random_key}"])
        assert f"Initial commit: {random_key}" in app.tools.git.capture(["log", "-1", "--oneline"])


def test_author_details(app: Application, mocker, default_git_author: GitAuthorConfig) -> None:  # type: ignore[no-untyped-def]
    # Test 1: Author details coming from env vars, set by the fixture
    assert app.tools.git.author_name == default_git_author.name
    assert app.tools.git.author_email == default_git_author.email
    # Clear the cached properties
    del app.tools.git.author_name
    del app.tools.git.author_email
    # Test 2: Author details coming from git config, not set by the fixture
    with EnvVars({GitEnvVars.AUTHOR_NAME: "", GitEnvVars.AUTHOR_EMAIL: ""}):
        mocker.patch("dda.tools.git.Git.capture", return_value="Foo Bar 2")
        assert app.tools.git.author_name == "Foo Bar 2"
        mocker.patch("dda.tools.git.Git.capture", return_value="foo@bar2.baz")
        assert app.tools.git.author_email == "foo@bar2.baz"


def test_get_remote(app: Application, temp_repo_with_remote: Path) -> None:
    with temp_repo_with_remote.as_cwd():
        assert app.tools.git.get_remote().url == "https://github.com/foo/bar"


# TODO: Add more testcases here with different refs
def test_get_commit(app: Application, temp_repo_with_remote: Path) -> None:
    with temp_repo_with_remote.as_cwd():
        random_key = random.randint(1, 1000000)
        app.tools.git.commit_file(Path("hello.txt"), content="world", commit_message=f"Brand-new commit: {random_key}")
        sha1 = app.tools.git.capture(["rev-parse", "HEAD"]).strip()
        timestamp = int(app.tools.git.capture(["show", "-s", "--format=%ct", sha1]).strip())
        commit = app.tools.git.get_commit()

        assert commit.sha1 == sha1
        assert commit.author == GitPersonDetails(app.tools.git.author_name, app.tools.git.author_email, timestamp)
        assert commit.committer == GitPersonDetails(app.tools.git.author_name, app.tools.git.author_email, timestamp)
        assert commit.message == f"Brand-new commit: {random_key}"


def test_commit_file(app: Application, temp_repo: Path) -> None:
    with temp_repo.as_cwd():
        app.tools.git.commit_file(Path("hello.txt"), content="world", commit_message="Brand-new commit")
        assert "Brand-new commit" in app.tools.git.capture(["log", "-1", "--oneline"])
        assert Path("hello.txt").read_text() == "world"


def test_get_patch(app: Application, temp_repo: Path) -> None:
    with temp_repo.as_cwd():
        contents = "hello, world\n"
        # Need to make an initial commit to have a valid diff
        app.tools.git.commit_file(Path("dummy"), content="", commit_message="Initial commit")
        app.tools.git.commit_file(Path("hello.txt"), content=contents, commit_message="New commit")
        diff_lines = app.tools.git._get_patch("HEAD^", "HEAD").splitlines()  # noqa: SLF001
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


def test_get_changes(app: Application, repo_setup_working_tree: tuple[Path, ChangeSet]) -> None:
    git: Git = app.tools.git
    temp_repo, expected_changeset = repo_setup_working_tree
    with temp_repo.as_cwd():
        # Setup: get the SHA1 of the HEAD commit
        root_sha1 = git.capture(["rev-parse", "HEAD"]).strip()

        # Case 1: Get the changes in the working tree
        changeset = git.get_changes("HEAD", start="HEAD", working_tree=True)
        assert_changesets_equal(changeset, expected_changeset)

        # Case 2: Get the changes of the HEAD commit - should have the same changeset as the working tree
        git.add(["."])
        git.commit("New commit")
        head_sha1 = git.capture(["rev-parse", "HEAD"]).strip()
        changeset = git.get_changes()
        assert_changesets_equal(changeset, expected_changeset)

        # Case 3: Get the changes between two arbitrary commits
        # Here it just happens to be HEAD but that should not matter
        changeset = git.get_changes(head_sha1, start=root_sha1)
        assert_changesets_equal(changeset, expected_changeset)

        # Case 4: Get changes from HEAD with working tree changes
        new_file = Path("new_file.txt")
        new_file.write_text("new file\n")
        changeset = git.get_changes(working_tree=True)
        new_expected_changeset = expected_changeset | ChangeSet({
            new_file: ChangedFile(path=new_file, type=ChangeType.ADDED, binary=False, patch="@@ -0,0 +1 @@\n+new file")
        })
        assert_changesets_equal(changeset, new_expected_changeset)


# TODO: Implement this test - diffing with a merge base
def test_get_changes_merge_base() -> None:
    pass
