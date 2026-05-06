# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.utils.fs import Path
    from dda.utils.git.remote import Remote


class Repo(ABC):
    """A git repository on the local filesystem at a known path."""

    def __init__(self, app: Application, path: Path) -> None:
        self._app = app
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @property
    def exists(self) -> bool:
        return self._path.is_dir()

    @property
    @abstractmethod
    def is_bare(self) -> bool: ...

    def fetch(self, remote: str = "origin", *, prune: bool = False) -> None:
        self._app.tools.git.fetch(remote, prune=prune, cwd=self._path)

    def has_ref(self, name: str) -> bool:
        return self._app.tools.git.has_ref(name, cwd=self._path)

    @cached_property
    def remote(self) -> Remote | None:
        return self._app.tools.git.get_remote(cwd=self._path)

    @property
    def org(self) -> str | None:
        return self.remote.org if self.remote else None

    @property
    def name(self) -> str:
        if self.remote:
            return self.remote.repo
        return self._path.name.removesuffix(".git")


class BareRepo(Repo):
    """A bare git repository (no working tree) at an arbitrary path."""

    is_bare = True

    def initialize(self, url: str) -> None:
        """Clone bare and configure origin/* refs so origin/HEAD and --base-ref resolve."""
        git = self._app.tools.git
        path_str = str(self._path)
        git.clone(url, self._path, bare=True)
        git.capture(["-C", path_str, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"])
        git.fetch("origin", cwd=self._path)
        git.capture(["-C", path_str, "remote", "set-head", "origin", "--auto"])

    def list_worktree_names(self) -> list[str]:
        """Names of subdirectories under {path}/worktrees/, or [] if absent."""
        worktrees_dir = self._path / "worktrees"
        if not worktrees_dir.is_dir():
            return []
        return [entry.name for entry in worktrees_dir.iterdir() if entry.is_dir()]

    def remove_worktree_entry(self, name: str) -> None:
        """Remove the {path}/worktrees/{name} metadata directory if it exists."""
        shutil.rmtree(self._path / "worktrees" / name, ignore_errors=True)


class Worktree(Repo):
    """A working-tree git checkout (main or linked) at an arbitrary path."""

    is_bare = False

    @cached_property
    def common_dir(self) -> Path:
        """The common git directory, resolved to absolute.

        Equals .git for the main worktree; points to the main repo's .git for linked worktrees.
        """
        from dda.utils.fs import Path

        raw = self._app.tools.git.capture(["rev-parse", "--git-common-dir"], cwd=str(self._path)).strip()
        return (self._path / raw).resolve()

    @property
    def is_linked(self) -> bool:
        """True for linked worktrees; False for the main worktree."""
        return (self._path / ".git").is_file()
