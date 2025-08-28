# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import random
from typing import TYPE_CHECKING

import pytest

from dda.tools.git import Git
from dda.utils.fs import Path

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
@pytest.fixture(name="create_commit_dummy_file")
def fixt_create_commit_dummy_file(
    app: Application,
    temp_repo: Path,
    set_commiter_details: None,  # noqa: ARG001
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
