# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from datetime import datetime

import pytest
from httpx import Response

from dda.utils.fs import Path
from dda.utils.git.changeset import ChangedFile, ChangeSet
from dda.utils.git.commit import Commit, GitPersonDetails
from dda.utils.git.remote import HTTPSRemote, Remote, SSHRemote, get_change_type_from_github_status


class TestRemoteClass:
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/foo/bar",
            "https://github.com/foo/bar.git",
            "git@github.com:foo/bar.git",
            "git@github.com:foo/bar",
            "https://gitlab.com/foo/bar",
            "https://gitlab.com/foo/bar.git",
            "git@gitlab.com:foo/bar.git",
            "git@gitlab.com:foo/bar",
        ],
    )
    def test_basic(self, url):
        remote = Remote.from_url(url=url)
        assert remote.url == url
        assert remote.org == "foo"
        assert remote.repo == "bar"
        assert remote.full_repo == "foo/bar"
        if url.startswith("https://"):
            assert isinstance(remote, HTTPSRemote)
            assert remote.protocol == "https"
        elif url.startswith("git@"):
            assert isinstance(remote, SSHRemote)
            assert remote.protocol == "git"

    @pytest.mark.parametrize(
        "github_payload_file",
        ["commit_example_dda_1425a34.json", "commit_example_multiple_parents.json", "commit_example_binary_files.json"],
    )
    def test_get_commit_and_changes_from_remote(self, mocker, github_payload_file):
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
        commit_url = data["commit"]["url"]
        remote = Remote.from_url(url=commit_url)

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
        remote_commit, commit_changes = remote.get_commit_and_changes(sha1)
        assert commit_changes == expected_commit_changes

        # Check all fields
        for field in ["sha1", "author", "committer", "message"]:
            assert getattr(expected_commit, field) == getattr(remote_commit, field)
