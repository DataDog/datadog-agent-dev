# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.utils.git.changeset import ChangeType
from dda.utils.git.commit import Commit, GitPersonDetails

if TYPE_CHECKING:
    from dda.utils.git.changeset import ChangeSet
    from dda.utils.git.remote import Remote


def get_github_url(remote: Remote) -> str:
    return f"https://github.com/{remote.full_repo}"


def get_github_api_url(remote: Remote) -> str:
    return f"https://api.github.com/repos/{remote.full_repo}"


def get_commit_github_url(remote: Remote, sha1: str) -> str:
    return f"{get_github_url(remote)}/commit/{sha1}"


def get_commit_github_api_url(remote: Remote, sha1: str) -> str:
    return f"{get_github_api_url(remote)}/commits/{sha1}"


def get_commit_and_changes_from_github(remote: Remote, sha1: str) -> tuple[Commit, ChangeSet]:
    """
    Get the details and set of changes for a given commit by querying the remote.
    """
    from datetime import datetime

    from dda.utils.fs import Path
    from dda.utils.git.changeset import ChangedFile, ChangeSet
    from dda.utils.git.github import get_commit_github_api_url
    from dda.utils.network.http.client import get_http_client

    client = get_http_client()
    data = client.get(get_commit_github_api_url(remote, sha1)).json()

    # Compute ChangeSet
    changes = ChangeSet(
        ChangedFile(
            path=Path(file_obj["filename"]),
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


def get_change_type_from_github_status(status: str) -> ChangeType:
    if status == "added":
        return ChangeType.ADDED
    if status == "modified":
        return ChangeType.MODIFIED
    if status == "removed":
        return ChangeType.DELETED

    msg = f"Invalid GitHub change type message: {status}"
    raise ValueError(msg)
