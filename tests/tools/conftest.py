import shutil
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING

import pytest

from dda.cli.application import Application
from dda.utils.fs import Path

if TYPE_CHECKING:
    from dda.tools.git import Git


def clear_cached_config(app: Application) -> None:
    if hasattr(app.config_file, "model"):
        del app.config_file.model

    if hasattr(app, "config"):
        del app.config

    if hasattr(app.tools.git, "author_name"):
        del app.tools.git.author_name

    if hasattr(app.tools.git, "author_email"):
        del app.tools.git.author_email


# Initialize a dummy repo in a temporary directory for the tests to use
@pytest.fixture
def temp_repo(app: Application, temp_dir: Path, set_git_author: None) -> Generator[Path, None, None]:  # noqa: ARG001
    git: Git = app.tools.git
    repo_path = temp_dir / "dummy-repo"
    repo_path.mkdir()  # Don't do exist_ok, the directory should not exist
    with repo_path.as_cwd():
        git.run(["init", "--initial-branch", "main"])
    yield repo_path
    # Cleanup

    shutil.rmtree(repo_path)


@pytest.fixture
def set_git_author(app: Application) -> Generator[None, None, None]:
    """
    Set the git author name and email to "Test Runner" and "test.runner@example.com" respectively.
    This is done by setting the values in the config file.
    Any commits made by `dda` will use these values, but any calls to `git config` will still return the global git config values.
    """
    old_name = app.config_file.data["tools"]["git"]["author_name"]
    old_email = app.config_file.data["tools"]["git"]["author_email"]
    app.config_file.data["tools"]["git"]["author_name"] = "Test Runner"
    app.config_file.data["tools"]["git"]["author_email"] = "test.runner@example.com"

    app.config_file.save()
    clear_cached_config(app)
    yield
    app.config_file.data["tools"]["git"]["author_name"] = old_name
    app.config_file.data["tools"]["git"]["author_email"] = old_email
    app.config_file.save()
    clear_cached_config(app)


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
