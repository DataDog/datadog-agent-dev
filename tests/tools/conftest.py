import shutil
from collections.abc import Callable, Generator

import msgspec
import pytest
from _pytest.fixtures import SubRequest

from dda.cli.application import Application
from dda.tools.git import Git
from dda.utils.fs import Path
from dda.utils.git.changeset import ChangeSet


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
    import shutil

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


@pytest.fixture
def temp_repo_with_remote(app: Application, temp_repo: Path) -> Path:
    with temp_repo.as_cwd():
        app.tools.git.run(["remote", "add", "origin", "https://github.com/foo/bar"])
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
        git.run(["add", "."])
        git.run(["commit", "-m", "Initial commit"])
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
            git.run(["add", "."])
            git.run(["commit", "-m", "Changed commit"])


def _load_changeset(filepath: Path) -> ChangeSet:
    with open(filepath, encoding="utf-8") as f:
        return msgspec.json.decode(f.read(), type=ChangeSet, dec_hook=ChangeSet.dec_hook)


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
