# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.utils.fs import Path
    from dda.utils.git.sha1hash import SHA1Hash


@dataclass
class Commit:
    """
    A Git commit, identified by its SHA-1 hash.
    """

    org: str
    repo: str
    sha1: SHA1Hash

    def __str__(self) -> str:
        return str(self.sha1)

    @property
    def full_repo(self) -> str:
        return f"{self.org}/{self.repo}"

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.full_repo}/commit/{self.sha1}"

    @property
    def github_api_url(self) -> str:
        return f"https://api.github.com/repos/{self.full_repo}/commits/{self.sha1}"

    @classmethod
    def head(cls, app: Application, repo_path: Path | None = None) -> Commit:
        """
        Get the current HEAD commit of the Git repository at the given path.
        If no path is given, use the current working directory.
        """
        return app.tools.git.get_head_commit(repo_path)
