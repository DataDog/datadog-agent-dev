# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import UTC, datetime

from httpx import Response

from dda.utils.fs import Path
from dda.utils.git.commit import Commit, CommitDetails
from dda.utils.git.remote import Remote


class TestCommitClass:
    def test_basic(self):
        commit = Commit(sha1="82ee754ca931816902ac7e6e38f66a51e65912f9")
        assert commit.sha1 == "82ee754ca931816902ac7e6e38f66a51e65912f9"

    def test_equality(self):
        commit1 = Commit(sha1="82ee754ca931816902ac7e6e38f66a51e65912f9")
        commit2 = Commit(sha1="82ee754ca931816902ac7e6e38f66a51e65912f9")

        assert commit1 == commit2


class TestCommitDetailsClass:
    def test_details(self):
        now = datetime.now(tz=UTC)
        commit_details = CommitDetails(
            author_name="John Doe",
            author_email="john.doe@example.com",
            datetime=now,
            message="This is a test message",
            parent_shas=["82ee754ca931816902ac7e6e38f66a51e65912f9"],
        )
        assert commit_details.author_name == "John Doe"
        assert commit_details.author_email == "john.doe@example.com"
        assert commit_details.datetime == now
        assert commit_details.message == "This is a test message"
        assert commit_details.parent_shas == ["82ee754ca931816902ac7e6e38f66a51e65912f9"]

    def test_details_github_git_equality(self, app, mocker):
        # Initialize commit object
        commit = Commit("1425a34f443f0b468e1739a06fcf97dfbf632594")

        # Mock HTTP client to return a known payload
        github_payload_file = Path(__file__).parent / "fixtures" / "github_payloads" / "commit_example_dda_1425a34.json"
        github_payload_str = github_payload_file.read_text(encoding="utf-8")
        mocker.patch(
            "dda.utils.network.http.client.HTTPClient.get",
            return_value=Response(status_code=200, content=github_payload_str),
        )
        github_details = Remote.from_url("https://github.com/foo/bar").get_details_and_changes_for_commit(commit)[0]

        # Mock Git.capture to return payload from file
        git_output_file = Path(__file__).parent / "fixtures" / "git_show_dda_1425a34.txt"
        git_output = git_output_file.read_text(encoding="utf-8")
        mocker.patch(
            "dda.tools.git.Git.capture",
            return_value=git_output,
        )

        # Get details from Git
        git_details = app.tools.git.get_commit_details(commit.sha1)
        assert github_details == git_details
