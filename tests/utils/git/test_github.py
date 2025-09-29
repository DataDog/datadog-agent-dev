# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import json
from datetime import datetime

import pytest
from httpx import Response

from dda.utils.fs import Path
from dda.utils.git.changeset import ChangedFile, ChangeSet
from dda.utils.git.commit import Commit, GitPersonDetails
from dda.utils.git.github import (
    get_change_type_from_github_status,
    get_commit_and_changes_from_github,
    get_commit_github_api_url,
    get_commit_github_url,
    get_github_api_url,
    get_github_url,
)
from dda.utils.git.remote import Remote


def test_get_github_url():
    remote = Remote("https://github.com/foo/bar")
    assert get_github_url(remote) == "https://github.com/foo/bar"


def test_get_github_api_url():
    remote = Remote("https://github.com/foo/bar")
    assert get_github_api_url(remote) == "https://api.github.com/repos/foo/bar"


def test_get_commit_github_url():
    remote = Remote("https://github.com/foo/bar")
    sha1 = "1234567890" * 4
    author = GitPersonDetails(name="a", email="a", timestamp=0)
    commit = Commit(sha1=sha1, author=author, committer=author, message="a")
    assert get_commit_github_url(remote, commit) == f"https://github.com/foo/bar/commit/{sha1}"


def test_get_commit_github_api_url():
    remote = Remote("https://github.com/foo/bar")
    sha1 = "1234567890" * 4
    author = GitPersonDetails(name="a", email="a", timestamp=0)
    commit = Commit(sha1=sha1, author=author, committer=author, message="a")
    assert get_commit_github_api_url(remote, commit) == f"https://api.github.com/repos/foo/bar/commits/{sha1}"


@pytest.mark.parametrize(
    "github_payload_file",
    ["commit_example_dda_1425a34.json", "commit_example_multiple_parents.json", "commit_example_binary_files.json"],
)
def test_get_commit_and_changes_from_github(mocker, github_payload_file):
    # Mock http client to return a known payload
    fixtures_file = Path(__file__).parent / "fixtures" / "github_payloads" / github_payload_file
    github_payload_str = fixtures_file.read_text(encoding="utf-8")
    mocker.patch(
        "dda.utils.network.http.client.HTTPClient.get",
        return_value=Response(status_code=200, content=github_payload_str),
    )

    # Create a commit object with details from the payload
    data = json.loads(github_payload_str)
    sha1 = data["sha"]
    commit_url = data["html_url"]
    remote_url = commit_url.split("/commit/")[0]
    remote = Remote(remote_url)

    author_timestamp = int(datetime.fromisoformat(data["commit"]["author"]["date"]).timestamp())
    author = GitPersonDetails(data["commit"]["author"]["name"], data["commit"]["author"]["email"], author_timestamp)
    commit_timestamp = int(datetime.fromisoformat(data["commit"]["committer"]["date"]).timestamp())
    committer = GitPersonDetails(
        data["commit"]["committer"]["name"], data["commit"]["committer"]["email"], commit_timestamp
    )
    message = data["commit"]["message"]

    expected_commit = Commit(
        sha1=sha1,
        author=author,
        committer=committer,
        message=message,
    )
    # Create a ChangeSet object
    changes = [
        ChangedFile(
            path=Path(file["filename"]),
            type=get_change_type_from_github_status(file["status"]),
            binary="patch" not in file,
            patch=file.get("patch", ""),
        )
        for file in data["files"]
    ]
    expected_commit_changes = ChangeSet.from_iter(changes)

    # Make the comparisons
    remote_commit, commit_changes = get_commit_and_changes_from_github(remote, sha1)
    assert commit_changes == expected_commit_changes

    # Check all fields
    for field in ["sha1", "author", "committer", "message"]:
        assert getattr(expected_commit, field) == getattr(remote_commit, field)
