# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from pathlib import Path

import pytest

from dda.utils.process import EnvVars


@pytest.fixture
def create_mock_github_module(mocker):
    # Create mock for commit author
    mock_author = mocker.Mock()
    mock_author.name = "Porco Rosso"
    mock_author.email = "porco.rosso@example.com"

    # Create mock for commit tree
    mock_tree = mocker.Mock()
    mock_tree.sha = "tree_sha_456"

    # Create mock for commit details
    mock_commit_detail = mocker.Mock()
    mock_commit_detail.message = "Better to be a pig than a fascist"
    mock_commit_detail.author = mock_author
    mock_commit_detail.tree = mock_tree

    # Create mock for the original commit
    mock_original_commit = mocker.Mock()
    mock_original_commit.sha = "1234567890"
    mock_original_commit.commit = mock_commit_detail

    # Create mock for backport commit
    mock_backport_commit = mocker.Mock()
    mock_backport_commit.sha = "backport_commit_sha_999"

    # Create mock for PR
    mock_pr = mocker.Mock()
    mock_pr.html_url = "<mock_pr_html_url>"
    mock_pr.add_to_labels = mocker.Mock()

    # Create mock for git ref
    mock_git_ref = mocker.Mock()
    mock_git_ref.object = mocker.Mock(sha="target_branch_sha_123")

    # Create mock repository with all needed methods
    mock_repo = mocker.Mock()
    mock_repo.get_branch.return_value = mocker.Mock()  # Branch exists
    mock_repo.get_git_ref.return_value = mock_git_ref
    mock_repo.get_git_commit.return_value = mocker.Mock()
    mock_repo.get_commit.return_value = mock_original_commit
    mock_repo.get_git_tree.return_value = mocker.Mock()
    mock_repo.create_git_commit.return_value = mock_backport_commit
    mock_repo.create_git_ref.return_value = mocker.Mock(ref="create_git_ref_ref_return_value")
    mock_repo.create_pull.return_value = mock_pr

    # Mock the Github client instance
    mock_github_instance = mocker.Mock()
    mock_github_instance.get_repo.return_value = mock_repo

    # Mock the github module since it's a lazy import inside the function
    # We need to mock the entire module in sys.modules
    mock_github_module = mocker.Mock()
    mock_github_module.Github.return_value = mock_github_instance
    mock_github_module.GithubException = Exception
    mocker.patch.dict("sys.modules", {"github": mock_github_module})

    return {
        "mock_github_module": mock_github_module,
        "mock_github_instance": mock_github_instance,
        "mock_repo": mock_repo,
        "mock_pr": mock_pr,
    }


def test_backport_ok(dda, create_mock_github_module):
    # Get mocks from the fixture
    mocks = create_mock_github_module

    # Run the command with test environment
    # Set CI=true to simulate running in CI
    # Use absolute path to fixture file
    fixture_path = os.path.join(Path(__file__).parent, "fixtures", "event_ok.json")
    with EnvVars({"CI": "true", "GITHUB_EVENT_PATH": str(fixture_path), "GITHUB_TOKEN": "test_github_token"}):
        result = dda("gh", "backport")

    # Verify the result
    result.check_exit_code(0)

    # Verify output contains expected messages
    assert "Backport #123 to target branch: v0.30.2" in result.output
    assert "Backport branch name: backport-123-to-v0.30.2" in result.output
    assert "Backport workflow finished, PR created: <mock_pr_html_url>" in result.output

    # Verify that GitHub API methods were called correctly
    mocks["mock_github_module"].Github.assert_called_once_with("test_github_token")
    mocks["mock_github_instance"].get_repo.assert_called_once_with("owner/repo")
    mocks["mock_repo"].get_branch.assert_called_once_with("v0.30.2")
    mocks["mock_repo"].get_git_ref.assert_called_once_with("heads/v0.30.2")
    mocks["mock_repo"].get_git_commit.assert_called_once_with("target_branch_sha_123")
    mocks["mock_repo"].get_commit.assert_called_once_with("1234567890")

    # Check create_git_commit was called with the correct co-author
    call_args = mocks["mock_repo"].create_git_commit.call_args
    assert call_args.kwargs["message"].endswith(
        "Co-authored-by: Porco Rosso <porco.rosso@example.com>\n"
    )  # One parent commit

    # Check create_git_ref was called correctly
    mocks["mock_repo"].create_git_ref.assert_called_once_with(
        ref="refs/heads/backport-123-to-v0.30.2", sha="backport_commit_sha_999"
    )

    # Check create_pull was called with correct arguments
    # Note: The actual fixture has a newline at the end of the body
    expected_body = """Backport 1234567890 from #123.

___

Awesome PR body

This is a PR that is awesome and should be backported to the v0.30.2 branch.
"""
    mocks["mock_repo"].create_pull.assert_called_once_with(
        title="[Backport v0.30.2] Awesome PR", body=expected_body, base="v0.30.2", head="backport-123-to-v0.30.2"
    )

    mocks["mock_pr"].add_to_labels.assert_called_once_with("label1", "label2", "backport", "bot")


def test_backport_not_merged(dda, create_mock_github_module):
    # Get mocks from the fixture
    mocks = create_mock_github_module

    # Run the command with test environment
    # Set CI=true to simulate running in CI
    # Use absolute path to fixture file
    fixture_path = os.path.join(Path(__file__).parent, "fixtures", "event_not_merged.json")
    with EnvVars({"CI": "true", "GITHUB_EVENT_PATH": str(fixture_path), "GITHUB_TOKEN": "test_github_token"}):
        result = dda("gh", "backport")

    # Verify the result
    result.check_exit_code(0)

    # Verify output contains expected messages
    assert "For security reasons, this action should only run on merged PRs." in result.output

    # Verify that GitHub API methods were not called
    assert not mocks["mock_github_module"].Github.called
    assert not mocks["mock_github_instance"].get_repo.called
    assert not mocks["mock_repo"].get_commit.called
    assert not mocks["mock_repo"].get_branch.called
    assert not mocks["mock_repo"].create_pull.called
    assert not mocks["mock_pr"].add_to_labels.called


def test_backport_no_backport_label(dda, create_mock_github_module):
    # Get mocks from the fixture
    mocks = create_mock_github_module

    # Run the command with test environment
    # Set CI=true to simulate running in CI
    # Use absolute path to fixture file
    fixture_path = os.path.join(Path(__file__).parent, "fixtures", "event_no_backport_label.json")
    with EnvVars({"CI": "true", "GITHUB_EVENT_PATH": str(fixture_path), "GITHUB_TOKEN": "test_github_token"}):
        result = dda("gh", "backport")

    # Verify the result
    result.check_exit_code(0)

    # Verify output contains expected messages
    assert "Synchronizing dependencies\nNo backport/<target> label found. Skipping backport." in result.output

    # Verify that GitHub API methods were not called
    assert not mocks["mock_github_module"].Github.called
    assert not mocks["mock_github_instance"].get_repo.called
    assert not mocks["mock_repo"].get_commit.called
    assert not mocks["mock_repo"].get_branch.called
    assert not mocks["mock_repo"].create_pull.called
    assert not mocks["mock_pr"].add_to_labels.called


def test_backport_not_running_in_ci(dda, create_mock_github_module):
    # Get mocks from the fixture
    mocks = create_mock_github_module

    # Run the command with test environment
    # Set CI=false to simulate running locally
    # Use absolute path to fixture file
    fixture_path = os.path.join(Path(__file__).parent, "fixtures", "event_ok.json")
    with EnvVars({
        "CI": "false",
        "GITHUB_ACTIONS": "false",
        "GITHUB_EVENT_PATH": str(fixture_path),
        "GITHUB_TOKEN": "test_github_token",
    }):
        result = dda("gh", "backport")

    # Verify the result
    result.check_exit_code(0)

    # Verify output contains expected messages
    assert (
        "This command is meant to be run in CI, not locally. Use `dda github backport` to run it in CI."
        in result.output
    )

    # Verify that GitHub API methods were called correctly
    assert not mocks["mock_github_module"].Github.called
    assert not mocks["mock_github_instance"].get_repo.called
    assert not mocks["mock_repo"].get_commit.called
    assert not mocks["mock_repo"].get_branch.called
    assert not mocks["mock_repo"].create_pull.called
    assert not mocks["mock_pr"].add_to_labels.called
