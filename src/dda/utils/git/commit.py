# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from msgspec import Struct, field

if TYPE_CHECKING:
    from datetime import datetime

    from dda.cli.application import Application
    from dda.utils.git.changeset import ChangeSet


class Commit(Struct, dict=True):
    """
    A Git commit, identified by its SHA-1 hash.
    """

    org: str
    repo: str
    sha1: str

    _details: CommitDetails | None = field(default=None)
    _changes: ChangeSet | None = field(default=None)

    def __post_init__(self) -> None:
        if len(self.sha1) != 40:  # noqa: PLR2004
            msg = "SHA-1 hash must be 40 characters long"
            raise ValueError(msg)
        for c in self.sha1:
            code = ord(c)
            if code not in range(48, 58) and code not in range(97, 103):
                msg = "SHA-1 hash must contain only hexadecimal characters"
                raise ValueError(msg)

    def __str__(self) -> str:
        return self.sha1

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
    def head(cls, app: Application) -> Commit:
        """
        Get the current HEAD commit of the Git repository in the current working directory.
        """
        return app.tools.git.get_head_commit()

    def compare_to(self, app: Application, other: Commit) -> ChangeSet:
        """
        Compare this commit to another commit.
        """
        return app.tools.git.get_changes_between_commits(self.sha1, other.sha1)

    def get_details_and_changes_from_github(self) -> tuple[CommitDetails, ChangeSet]:
        """
        Get the details and set of changes for this commit by querying the GitHub API.
        Unlike the similar get_*_from_git() methods, this does not
        require a local clone of the repository or an Application instance.

        Prefer to use get_*_from_git() methods when possible, as they do not require making HTTP calls.
        """
        from datetime import datetime

        from dda.utils.fs import Path
        from dda.utils.git.changeset import ChangeSet, ChangeType, FileChanges
        from dda.utils.network.http.client import get_http_client

        client = get_http_client()
        data = client.get(self.github_api_url).json()

        # Compute ChangeSet
        changes = ChangeSet.from_iter(
            FileChanges(
                file=Path(file_obj["filename"]),
                type=ChangeType.from_github_status(file_obj["status"]),
                patch=file_obj["patch"],
            )
            for file_obj in data["files"]
        )
        self._changes = changes

        self._details = CommitDetails(
            author_name=data["commit"]["author"]["name"],
            author_email=data["commit"]["author"]["email"],
            datetime=datetime.fromisoformat(data["commit"]["author"]["date"]),
            message=data["commit"]["message"],
            parent_shas=[parent["sha"] for parent in data.get("parents", [])],
        )

        return self.details, self.changes

    def get_details_from_github(self) -> CommitDetails:
        return self.get_details_and_changes_from_github()[0]

    def get_details_from_git(self, app: Application) -> CommitDetails:
        """
        Get the details of this commit by querying the local Git repository.
        This requires an Application instance to access the Git tool.

        Prefer to use this method when possible, as it is much faster than
        querying the GitHub API.
        """
        self._details = app.tools.git.get_commit_details(self.sha1)
        return self.details

    def get_changes_from_github(self) -> ChangeSet:
        return self.get_details_and_changes_from_github()[1]

    def get_changes_from_git(self, app: Application) -> ChangeSet:
        self._changes = app.tools.git.get_commit_changes(self.sha1)
        return self.changes

    @cached_property
    def details(self) -> CommitDetails:
        if self._details is None:
            msg = "Commit details have not been fetched yet. Call one of the get_details_from_*() methods first."
            raise AttributeError(msg)
        return self._details

    @cached_property
    def changes(self) -> ChangeSet:
        if self._changes is None:
            msg = "Commit changes have not been fetched yet. Call one of the get_changes_from_*() methods first."
            raise AttributeError(msg)
        return self._changes

    # Proxy properties to access details directly from the Commit object
    @property
    def author_name(self) -> str:
        return self.details.author_name

    @property
    def author_email(self) -> str:
        return self.details.author_email

    @property
    def datetime(self) -> datetime:
        return self.details.datetime

    @property
    def message(self) -> str:
        return self.details.message

    @property
    def parent_shas(self) -> list[str]:
        return self.details.parent_shas


class CommitDetails(Struct):
    author_name: str
    author_email: str
    datetime: datetime
    message: str
    parent_shas: list[str]
