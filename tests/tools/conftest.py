# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from dda.cli.application import Application
    from dda.tools.git import Git


# Initialize a dummy repo in a temporary directory for the tests to use
@pytest.fixture
def temp_repo(app: Application, temp_dir: Path, set_git_author: None) -> Path:  # noqa: ARG001
    repo_path = temp_dir / "dummy-repo"
    repo_path.mkdir()  # Don't do exist_ok, the directory should not exist
    with repo_path.as_cwd():
        app.subprocess.run(["git", "init", "--initial-branch", "main"])
    return repo_path


@pytest.fixture
def set_git_author(app: Application) -> Generator[None, None, None]:
    """
    Set the git author name and email to "Test Runner" and "test.runner@example.com" respectively.
    This is done by setting the values in the config file.
    Any commits made by `dda` will use these values, but any calls to `git config` will still return the global git config values.
    """
    old_name = app.config_file.data["tools"]["git"]["author"]["name"]
    old_email = app.config_file.data["tools"]["git"]["author"]["email"]
    app.config_file.data["tools"]["git"]["author"]["name"] = "Test Runner"
    app.config_file.data["tools"]["git"]["author"]["email"] = "test.runner@example.com"

    app.config_file.save()
    yield
    app.config_file.data["tools"]["git"]["author"]["name"] = old_name
    app.config_file.data["tools"]["git"]["author"]["email"] = old_email
    app.config_file.save()


# Create a dummy file in the repository - uses the previously initialized dummy repo and the "fixture factory" pattern
@pytest.fixture
def create_commit_dummy_file(
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
            git.run(["commit", "-m", commit_message])

    return _create_commit_dummy_file
