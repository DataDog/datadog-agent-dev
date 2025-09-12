# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import UTC, datetime

import pytest
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

        # Basic equality
        assert commit1 == commit2

        # Add details to one of the commits
        commit1.__dict__["details"] = CommitDetails(
            author_name="John Doe",
            author_email="john.doe@example.com",
            datetime=datetime.now(tz=UTC),
            message="This is a test message",
            parent_shas=["1234567890" * 4],
        )
        # Should still be equal
        with pytest.raises(AttributeError):
            commit2.details  # noqa: B018
        assert commit1 == commit2

    # Already tested in tools/test_git.py
    def test_head(self):
        pass

    # Already tested in tools/test_git.py
    def test_compare_to(self, app):
        pass

    # Already tested in test_remote.py
    def test_get_commit_details_from_remote(self):
        pass

    # Already tested in tools/test_git.py
    def test_get_commit_details_from_git(self):
        pass

    def test_properties_proxying(self):
        commit = Commit("1425a34f443f0b468e1739a06fcf97dfbf632594")
        details_dict = {
            "author_name": "John Doe",
            "author_email": "john.doe@example.com",
            "datetime": datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC),
            "message": "Add new feature for testing",
            "parent_shas": ["82ee754ca931816902ac7e6e38f66a51e65912f9"],
        }
        commit_details = CommitDetails(**details_dict)
        commit.__dict__["details"] = commit_details
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
        github_details = commit.get_details_from_remote(Remote("https://github.com/foo/bar"))

        # Mock Git.capture to return payload from file
        git_output_file = Path(__file__).parent / "fixtures" / "git_show_dda_1425a34.txt"
        git_output = git_output_file.read_text(encoding="utf-8")
        mocker.patch(
            "dda.tools.git.Git.capture",
            return_value=git_output,
        )

        # Get details from Git
        git_details = commit.get_details_from_git(app)
        assert github_details == git_details
