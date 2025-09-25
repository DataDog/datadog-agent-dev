# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar, Literal

from dda.utils.git.changeset import ChangeType
from dda.utils.git.commit import Commit, GitPersonDetails

if TYPE_CHECKING:
    from dda.utils.git.changeset import ChangeSet


class Remote(ABC):
    protocol: ClassVar[Literal["https", "git"]]

    @classmethod
    def from_url(cls, url: str) -> Remote:
        if url.startswith("https://"):
            return HTTPSRemote(url)
        if url.startswith("git@"):
            return SSHRemote(url)
        msg = f"Invalid protocol: {url}"
        raise ValueError(msg)

    def __init__(self, url: str) -> None:
        self.url = url

    @property
    @abstractmethod
    def org(self) -> str:
        """
        The name of the organization the remote belongs to.
        """

    @property
    @abstractmethod
    def repo(self) -> str:
        """
        The name of the repository.
        """

    @cached_property
    def full_repo(self) -> str:
        return f"{self.org}/{self.repo}"

    def get_commit_and_changes(self, sha1: str) -> tuple[Commit, ChangeSet]:
        """
        Get the details and set of changes for a given commit by querying the remote.
        """
        from datetime import datetime

        from dda.utils.fs import Path
        from dda.utils.git.changeset import ChangedFile, ChangeSet
        from dda.utils.git.github import get_commit_github_api_url
        from dda.utils.network.http.client import get_http_client

        client = get_http_client()
        data = client.get(get_commit_github_api_url(self, sha1)).json()

        # Compute ChangeSet
        changes = ChangeSet.from_iter(
            ChangedFile(
                file=Path(file_obj["filename"]),
                type=get_change_type_from_github_status(file_obj["status"]),
                # GitHub does not have anything else to indicate binary files
                binary="patch" not in file_obj,
                patch=file_obj.get("patch", ""),
            )
            for file_obj in data["files"]
        )

        author_timestamp = int(datetime.fromisoformat(data["commit"]["author"]["date"]).timestamp())
        author = GitPersonDetails(data["commit"]["author"]["name"], data["commit"]["author"]["email"], author_timestamp)
        commit_timestamp = int(datetime.fromisoformat(data["commit"]["committer"]["date"]).timestamp())
        committer = GitPersonDetails(
            data["commit"]["committer"]["name"], data["commit"]["committer"]["email"], commit_timestamp
        )
        message = data["commit"]["message"]

        details = Commit(
            sha1=sha1,
            author=author,
            committer=committer,
            message=message,
        )

        return details, changes


class HTTPSRemote(Remote):
    protocol: ClassVar[Literal["https"]] = "https"

    @cached_property
    def org(self) -> str:
        return self.url.split("/")[3]

    @cached_property
    def repo(self) -> str:
        return self.url.removesuffix(".git").rsplit("/", 1)[-1]


class SSHRemote(Remote):
    protocol: ClassVar[Literal["git"]] = "git"

    @cached_property
    def org(self) -> str:
        return self.url.split(":")[1].split("/")[0]

    @cached_property
    def repo(self) -> str:
        return self.url.split(":")[1].split("/")[-1].removesuffix(".git")


def get_change_type_from_github_status(status: str) -> ChangeType:
    if status == "added":
        return ChangeType.ADDED
    if status == "modified":
        return ChangeType.MODIFIED
    if status == "removed":
        return ChangeType.DELETED

    msg = f"Invalid GitHub change type message: {status}"
    raise ValueError(msg)
