# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from datetime import datetime

import pytest
from httpx import Response

from dda.utils.fs import Path
from dda.utils.git.changeset import ChangeSet, FileChanges
from dda.utils.git.commit import Commit, CommitDetails
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
        remote = Remote(url=url)
        assert remote.url == url
        assert remote.org == "foo"
        assert remote.repo == "bar"
        assert remote.full_repo == "foo/bar"
        assert remote.github_url == "https://github.com/foo/bar"
        assert remote.github_api_url == "https://api.github.com/repos/foo/bar"
        if url.startswith("https://"):
            assert isinstance(remote, HTTPSRemote)
            assert remote.protocol == "https"
        elif url.startswith("git@"):
            assert isinstance(remote, SSHRemote)
            assert remote.protocol == "git"

    def test_get_commit_github_url(self):
        remote = Remote(url="https://github.com/foo/bar")
        sha1 = "1234567890" * 4
        commit = Commit(sha1=sha1)
        assert remote.get_commit_github_url(commit) == f"https://github.com/foo/bar/commit/{sha1}"

    def test_get_commit_github_api_url(self):
        remote = Remote(url="https://github.com/foo/bar")
        sha1 = "1234567890" * 4
        commit = Commit(sha1=sha1)
        assert remote.get_commit_github_api_url(commit) == f"https://api.github.com/repos/foo/bar/commits/{sha1}"

    @pytest.mark.parametrize(
        "github_payload_file",
        ["commit_example_dda_1425a34.json", "commit_example_multiple_parents.json"],
    )
    def test_get_commit_details_and_changes_from_remote(self, mocker, github_payload_file):
        # Mock http client to return a known payload
        fixtures_file = Path(__file__).parent / "fixtures" / "github_payloads" / github_payload_file
        github_payload_str = fixtures_file.read_text(encoding="utf-8")
        mocker.patch(
            "dda.utils.network.http.client.HTTPClient.get",
            return_value=Response(status_code=200, content=github_payload_str),
        )

        # Create a commit object with details from the payload
        github_payload = json.loads(github_payload_str)
        sha1 = github_payload["sha"]
        commit_url = github_payload["commit"]["url"]
        remote = Remote(url=commit_url)
        commit = Commit(sha1=sha1)

        # Create a CommitDetails object
        expected_commit_details = CommitDetails(
            author_name=github_payload["commit"]["author"]["name"],
            author_email=github_payload["commit"]["author"]["email"],
            datetime=datetime.fromisoformat(github_payload["commit"]["author"]["date"]),
            message=github_payload["commit"]["message"],
            parent_shas=[parent["sha"] for parent in github_payload["parents"]],
        )

        # Create a ChangeSet object
        changes = [
            FileChanges(
                file=Path(file["filename"]),
                type=get_change_type_from_github_status(file["status"]),
                patch=file["patch"],
            )
            for file in github_payload["files"]
        ]
        expected_commit_changes = ChangeSet.from_iter(changes)

        # Make the comparisons
        commit_details, commit_changes = remote.get_details_and_changes_for_commit(commit)
        assert commit_details == expected_commit_details
        assert commit_changes == expected_commit_changes
