# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import UTC, datetime

from httpx import Response

from dda.utils.fs import Path
from dda.utils.git.commit import Commit, GitPersonDetails
from dda.utils.git.github import get_commit_and_changes_from_github
from dda.utils.git.remote import Remote


class TestCommitClass:
    def test_basic(self):
        now = int(datetime.now(tz=UTC).timestamp())
        author = GitPersonDetails(name="John Doe", email="john.doe@example.com", timestamp=now)
        committer = GitPersonDetails(name="Jane Doe", email="jane.doe@example.com", timestamp=now)
        commit = Commit(
            sha1="82ee754ca931816902ac7e6e38f66a51e65912f9",
            author=author,
            committer=committer,
            message="This is a test message",
        )
        assert commit.sha1 == "82ee754ca931816902ac7e6e38f66a51e65912f9"
        assert commit.author == author
        assert commit.committer == committer
        assert commit.message == "This is a test message"

    def test_equality(self):
        # Should stay equal with different details as long as the sha1 is the same
        author1 = GitPersonDetails(name="a", email="a", timestamp=0)
        author2 = GitPersonDetails(name="b", email="b", timestamp=500)
        commit1 = Commit(sha1="a" * 40, author=author1, committer=author1, message="a")
        commit2 = Commit(sha1="a" * 40, author=author2, committer=author2, message="b")

        assert commit1 == commit2

    def test_commit_datetime(self):
        now = int(datetime.now(tz=UTC).timestamp())
        commit = Commit(
            sha1="82ee754ca931816902ac7e6e38f66a51e65912f9",
            author=GitPersonDetails(name="John Doe", email="john.doe@example.com", timestamp=now),
            committer=GitPersonDetails(name="Jane Doe", email="jane.doe@example.com", timestamp=now),
            message="This is a test message",
        )
        assert commit.committer_datetime == datetime.fromtimestamp(now, tz=UTC)

    def test_details_github_git_equality(self, app, mocker, helpers):
        # Initialize referenced commit object
        reference_commit = Commit(
            sha1="1425a34f443f0b468e1739a06fcf97dfbf632594",
            author=GitPersonDetails(
                name="Pierre-Louis Veyrenc", email="pierrelouis.veyrenc@datadoghq.com", timestamp=1755873573
            ),
            committer=GitPersonDetails(name="GitHub", email="noreply@github.com", timestamp=1755873573),
            message=helpers.dedent(
                """
                [ACIX-973] Implement `info owners code` command (#167)

                * feat(info): Add stub for new `info owners code` command and groups

                * feat(info): Add and require new `codeowners` dep group

                * feat(info): Basic body for the task

                * feat(info): Support getting codeowners for multiple files at once

                * feat(info): Add pretty-printing mechanism

                * feat(tests): Add test helper functions and first test for `dda info owners code`

                * feat(tests): Add more tests for `dda info owners code`

                * chore: Linter and formatter fixes

                * refactor: Address review comments

                * fix(info): Human output on `stdout`

                * feat(tests): Add a couple more tests

                * fix(info): Always use POSIX paths with codeowners library

                This was causing test failures on Windows, as the codeowners library expects paths to be in POSIX format.
                Also some tests were not using the correct path separator, which was causing issues on Windows.

                * refactor(info): Post-review code style tweaks

                * use `Path.read_text` instead of manually `open`ing
                * Use walrus operator instead of intermediary list
                * Use pytest fixtures and `dedent` helper function in test code

                * refactor(info): Rename `--config` argument to `--owners`

                * feat(tests): Use pytest features for `test_code.py`

                * Use fixtures, and in particular the "Factories as fixtures" pattern
                * Use parametrization for better defining test cases
                * Improve cleanup logic by including it in the fixtures

                * chore(tests): Add extra typing info and address linter complains""",
            ),
        )

        # Mock HTTP client to return a known payload
        github_payload_file = Path(__file__).parent / "fixtures" / "github_payloads" / "commit_example_dda_1425a34.json"
        github_payload_str = github_payload_file.read_text(encoding="utf-8")
        mocker.patch(
            "dda.utils.network.http.client.HTTPClient.get",
            return_value=Response(status_code=200, content=github_payload_str),
        )
        github_commit = get_commit_and_changes_from_github(Remote("https://github.com/foo/bar"), reference_commit.sha1)[
            0
        ]

        # Mock Git.capture to return payload from file
        git_output_file = Path(__file__).parent / "fixtures" / "git_show_dda_1425a34.txt"
        git_output = git_output_file.read_text(encoding="utf-8")
        mocker.patch(
            "dda.tools.git.Git.capture",
            return_value=git_output,
        )

        # Get commit from Git
        git_commit = app.tools.git.get_commit(reference_commit.sha1)

        # Check all fields
        for field in ["sha1", "author", "committer", "message"]:
            assert getattr(reference_commit, field) == getattr(github_commit, field) == getattr(git_commit, field)
