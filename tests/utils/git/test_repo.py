# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dda.utils.fs import Path
from dda.utils.git.repo import BareRepo, Worktree

if TYPE_CHECKING:
    from dda.cli.application import Application


@pytest.fixture
def source_repo(app: Application, tmp_path: Path) -> Path:
    path = Path(tmp_path) / "source"
    path.mkdir()
    app.subprocess.capture(["git", "init", "--initial-branch", "main"], cwd=str(path))
    app.tools.git.capture(["commit", "--allow-empty", "-m", "init"], cwd=str(path))
    return path


class TestBareRepo:
    def test_exists_false(self, app: Application, tmp_path: Path) -> None:
        assert not BareRepo(app, Path(tmp_path) / "repo.git").exists

    def test_exists_true(self, app: Application, tmp_path: Path, source_repo: Path) -> None:
        bare = BareRepo(app, Path(tmp_path) / "repo.git")
        bare.initialize(str(source_repo))
        assert bare.exists

    def test_is_bare(self, app: Application, tmp_path: Path) -> None:
        assert BareRepo(app, Path(tmp_path) / "repo.git").is_bare

    def test_initialize_populates_origin_refs(self, app: Application, tmp_path: Path, source_repo: Path) -> None:
        bare = BareRepo(app, Path(tmp_path) / "repo.git")
        bare.initialize(str(source_repo))
        assert bare.has_ref("origin/main")
        assert bare.has_ref("origin/HEAD")

    def test_has_ref_missing(self, app: Application, tmp_path: Path, source_repo: Path) -> None:
        bare = BareRepo(app, Path(tmp_path) / "repo.git")
        bare.initialize(str(source_repo))
        assert not bare.has_ref("origin/nonexistent-xyz")

    def test_fetch(self, app: Application, tmp_path: Path, source_repo: Path) -> None:
        bare = BareRepo(app, Path(tmp_path) / "repo.git")
        bare.initialize(str(source_repo))
        app.tools.git.capture(["commit", "--allow-empty", "-m", "second"], cwd=str(source_repo))
        bare.fetch()  # must not raise

    def test_list_worktree_names_empty(self, app: Application, tmp_path: Path, source_repo: Path) -> None:
        bare = BareRepo(app, Path(tmp_path) / "repo.git")
        bare.initialize(str(source_repo))
        assert bare.list_worktree_names() == []

    def test_list_worktree_names(self, app: Application, tmp_path: Path, source_repo: Path) -> None:
        path = Path(tmp_path) / "repo.git"
        bare = BareRepo(app, path)
        bare.initialize(str(source_repo))
        (path / "worktrees" / "my-worktree").mkdir(parents=True)
        assert bare.list_worktree_names() == ["my-worktree"]

    def test_remove_worktree_entry(self, app: Application, tmp_path: Path, source_repo: Path) -> None:
        path = Path(tmp_path) / "repo.git"
        bare = BareRepo(app, path)
        bare.initialize(str(source_repo))
        wt = path / "worktrees" / "my-worktree"
        wt.mkdir(parents=True)
        bare.remove_worktree_entry("my-worktree")
        assert not wt.exists()

    def test_remove_worktree_entry_nonexistent(self, app: Application, tmp_path: Path, source_repo: Path) -> None:
        bare = BareRepo(app, Path(tmp_path) / "repo.git")
        bare.initialize(str(source_repo))
        bare.remove_worktree_entry("nonexistent")  # must not raise

    def test_name_fallback(self, app: Application, tmp_path: Path) -> None:
        path = Path(tmp_path) / "my-repo.git"
        app.subprocess.capture(["git", "init", "--bare", str(path)])
        assert BareRepo(app, path).name == "my-repo"

    def test_name_no_git_suffix(self, app: Application, tmp_path: Path) -> None:
        path = Path(tmp_path) / "my-repo"
        app.subprocess.capture(["git", "init", "--bare", str(path)])
        assert BareRepo(app, path).name == "my-repo"


class TestWorktree:
    def test_exists_false(self, app: Application, tmp_path: Path) -> None:
        assert not Worktree(app, Path(tmp_path) / "nonexistent").exists

    def test_exists_true(self, app: Application, temp_repo: Path) -> None:
        assert Worktree(app, temp_repo).exists

    def test_is_bare_false(self, app: Application, temp_repo: Path) -> None:
        assert not Worktree(app, temp_repo).is_bare

    def test_is_linked_false(self, app: Application, temp_repo: Path) -> None:
        assert not Worktree(app, temp_repo).is_linked

    def test_is_linked_true(self, app: Application, tmp_path: Path, temp_repo: Path) -> None:
        app.tools.git.capture(["commit", "--allow-empty", "-m", "init"], cwd=str(temp_repo))
        wt_path = Path(tmp_path) / "wt"
        app.tools.git.capture(["worktree", "add", "-b", "feat", str(wt_path), "HEAD"], cwd=str(temp_repo))
        assert Worktree(app, wt_path).is_linked

    def test_common_dir_main_worktree(self, app: Application, temp_repo: Path) -> None:
        wt = Worktree(app, temp_repo)
        assert wt.common_dir == (temp_repo / ".git").resolve()

    def test_common_dir_linked_worktree(self, app: Application, tmp_path: Path, temp_repo: Path) -> None:
        app.tools.git.capture(["commit", "--allow-empty", "-m", "init"], cwd=str(temp_repo))
        wt_path = Path(tmp_path) / "wt"
        app.tools.git.capture(["worktree", "add", "-b", "feat", str(wt_path), "HEAD"], cwd=str(temp_repo))
        wt = Worktree(app, wt_path)
        assert wt.common_dir == (temp_repo / ".git").resolve()

    def test_name_fallback(self, app: Application, temp_repo: Path) -> None:
        assert Worktree(app, temp_repo).name == "dummy-repo"
