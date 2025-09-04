# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from httpx import Response

from dda.utils.fs import Path
from dda.utils.git.changeset import ChangeSet, ChangeType, FileChanges
from dda.utils.git.commit import Commit, CommitDetails, SHA1Hash


class TestCommitClass:
    def test_basic(self):
        commit = Commit(org="foo", repo="bar", sha1=SHA1Hash("82ee754ca931816902ac7e6e38f66a51e65912f9"))
        assert commit.org == "foo"
        assert commit.repo == "bar"
        assert commit.sha1 == "82ee754ca931816902ac7e6e38f66a51e65912f9"
        assert commit.full_repo == "foo/bar"
        assert commit.github_url == "https://github.com/foo/bar/commit/82ee754ca931816902ac7e6e38f66a51e65912f9"
        assert (
            commit.github_api_url
            == "https://api.github.com/repos/foo/bar/commits/82ee754ca931816902ac7e6e38f66a51e65912f9"
        )

    # Already tested in tools/test_git.py
    def test_head(self):
        pass

    @pytest.mark.parametrize(
        "github_payload_file",
        ["commit_example_dda_1425a34.json", "commit_example_multiple_parents.json"],
    )
    def test_get_commit_details_and_changes_from_github(self, mocker, github_payload_file):
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
        org = commit_url.split("/")[4]
        repo = commit_url.split("/")[5]
        commit = Commit(org=org, repo=repo, sha1=SHA1Hash(sha1))

        # Create a CommitDetails object
        expected_commit_details = CommitDetails(
            author_name=github_payload["commit"]["author"]["name"],
            author_email=github_payload["commit"]["author"]["email"],
            datetime=datetime.fromisoformat(github_payload["commit"]["author"]["date"]),
            message=github_payload["commit"]["message"],
            parent_shas=[SHA1Hash(parent["sha"]) for parent in github_payload["parents"]],
        )

        # Create a ChangeSet object
        expected_commit_changes = ChangeSet()
        for file in github_payload["files"]:
            expected_commit_changes.add(
                FileChanges(
                    file=Path(file["filename"]), type=ChangeType.from_github_status(file["status"]), patch=file["patch"]
                )
            )

        # Make the comparisons
        commit_details, commit_changes = commit.get_details_and_changes_from_github()
        assert commit_details == expected_commit_details
        assert commit_changes == expected_commit_changes

    # Already tested in tools/test_git.py
    def test_get_commit_details_from_git(self):
        pass

    def test_properties_proxying(self):
        commit = Commit("DataDog", "datadog-agent-dev", SHA1Hash("1425a34f443f0b468e1739a06fcf97dfbf632594"))
        details_dict = {
            "author_name": "John Doe",
            "author_email": "john.doe@example.com",
            "datetime": datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC),
            "message": "Add new feature for testing",
            "parent_shas": [SHA1Hash("82ee754ca931816902ac7e6e38f66a51e65912f9")],
        }
        commit_details = CommitDetails(**details_dict)
        commit._details = commit_details  # noqa: SLF001
        assert commit.details == commit_details
        for prop, expected_value in details_dict.items():
            assert getattr(commit, prop) == getattr(commit_details, prop)
            assert getattr(commit, prop) == expected_value


class TestCommitDetailsClass:
    def test_details(self):
        now = datetime.now(tz=UTC)
        commit_details = CommitDetails(
            author_name="John Doe",
            author_email="john.doe@example.com",
            datetime=now,
            message="This is a test message",
            parent_shas=[SHA1Hash("82ee754ca931816902ac7e6e38f66a51e65912f9")],
        )
        assert commit_details.author_name == "John Doe"
        assert commit_details.author_email == "john.doe@example.com"
        assert commit_details.datetime == now
        assert commit_details.message == "This is a test message"
        assert commit_details.parent_shas == [SHA1Hash("82ee754ca931816902ac7e6e38f66a51e65912f9")]

    def test_details_github_git_equality(self, app, mocker):
        # Initialize commit object
        commit = Commit("DataDog", "datadog-agent-dev", SHA1Hash("1425a34f443f0b468e1739a06fcf97dfbf632594"))

        # Mock HTTP client to return a known payload
        github_payload_file = Path(__file__).parent / "fixtures" / "github_payloads" / "commit_example_dda_1425a34.json"
        github_payload_str = github_payload_file.read_text(encoding="utf-8")
        mocker.patch(
            "dda.utils.network.http.client.HTTPClient.get",
            return_value=Response(status_code=200, content=github_payload_str),
        )
        github_details = commit.get_details_from_github()

        # Mock Git.capture to return payload from file
        git_output_file = Path(__file__).parent / "fixtures" / "git_show_dda_1425a34.txt"
        git_output = git_output_file.read_text(encoding="utf-8")
        mocker.patch(
            "dda.tools.git.Git.capture",
            return_value=git_output,
        )

        # Get details from Git
        git_details = commit.get_details_from_git(app, repo_path=Path(__file__).parent.parent.parent.parent)
        assert github_details == git_details
