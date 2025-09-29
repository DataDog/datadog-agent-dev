# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import msgspec
import pytest

from dda.config.model import dec_hook
from dda.utils.fs import Path
from dda.utils.git.changeset import ChangeSet

if TYPE_CHECKING:
    from _pytest.fixtures import SubRequest

    from dda.cli.application import Application
    from dda.tools.git import Git


# Initialize a dummy repo in a temporary directory for the tests to use
@pytest.fixture
def temp_repo(app: Application, temp_dir: Path) -> Path:
    repo_path = temp_dir / "dummy-repo"
    repo_path.mkdir()  # Don't do exist_ok, the directory should not exist
    with repo_path.as_cwd():
        app.subprocess.capture(["git", "init", "--initial-branch", "main"])
    return repo_path


@pytest.fixture
def temp_repo_with_remote(app: Application, temp_repo: Path) -> Path:
    with temp_repo.as_cwd():
        app.tools.git.capture(["remote", "add", "origin", "https://github.com/foo/bar"])
    return temp_repo


REPO_TESTCASES = [path.name for path in (Path(__file__).parent / "fixtures" / "repo_states").iterdir()]


def _make_repo_changes(
    git: Git, temp_repo: Path, base_dir: Path, changed_dir: Path, *, commit_end: bool = True
) -> None:
    with temp_repo.as_cwd():
        # Create base commit
        # -- Copy files from base to temp_repo
        for file in base_dir.iterdir():
            shutil.copy(file, temp_repo / file.name)
        # -- Create commit
        git.capture(["add", "."])
        git.capture(["commit", "-m", "Initial commit"])
        # Create changed commit
        # -- Remove all files from temp_repo
        for file in temp_repo.iterdir():
            if file.is_file():
                file.unlink()
        # -- Copy files from changed to temp_repo
        for file in changed_dir.iterdir():
            shutil.copy(file, temp_repo / file.name)
        # -- Create commit if requested, otherwise leave working tree changes
        if commit_end:
            git.capture(["add", "."])
            git.capture(["commit", "-m", "Changed commit"])


def _load_changeset(filepath: Path) -> ChangeSet:
    with open(filepath, encoding="utf-8") as f:
        return msgspec.json.decode(f.read(), type=ChangeSet, dec_hook=dec_hook)


@pytest.fixture(params=REPO_TESTCASES)
def repo_setup(app: Application, temp_repo: Path, request: SubRequest) -> tuple[Path, ChangeSet]:
    git: Git = app.tools.git
    fixtures_dir = Path(__file__).parent / "fixtures" / "repo_states"
    base_dir: Path = fixtures_dir / request.param / "base"
    changed_dir: Path = fixtures_dir / request.param / "changed"

    # Make repo changes
    _make_repo_changes(git, temp_repo, base_dir, changed_dir, commit_end=True)

    # Load expected changeset
    expected_changeset = _load_changeset(fixtures_dir / request.param / "expected_changeset.json")

    return temp_repo, expected_changeset


@pytest.fixture(params=REPO_TESTCASES)
def repo_setup_working_tree(app: Application, temp_repo: Path, request: SubRequest) -> tuple[Path, ChangeSet]:
    git: Git = app.tools.git
    fixtures_dir = Path(__file__).parent / "fixtures" / "repo_states"
    base_dir: Path = fixtures_dir / request.param / "base"
    changed_dir: Path = fixtures_dir / request.param / "changed"

    # Make repo changes
    _make_repo_changes(git, temp_repo, base_dir, changed_dir, commit_end=False)

    # Load expected changeset
    expected_changeset = _load_changeset(fixtures_dir / request.param / "expected_changeset.json")

    return temp_repo, expected_changeset
