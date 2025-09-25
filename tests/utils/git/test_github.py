# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from dda.utils.git.commit import Commit
from dda.utils.git.github import get_commit_github_api_url, get_commit_github_url, get_github_api_url, get_github_url
from dda.utils.git.remote import Remote


def test_get_github_url():
    remote = Remote.from_url(url="https://github.com/foo/bar")
    assert get_github_url(remote) == "https://github.com/foo/bar"


def test_get_github_api_url():
    remote = Remote.from_url(url="https://github.com/foo/bar")
    assert get_github_api_url(remote) == "https://api.github.com/repos/foo/bar"


def test_get_commit_github_url():
    remote = Remote.from_url(url="https://github.com/foo/bar")
    sha1 = "1234567890" * 4
    commit = Commit(sha1=sha1, author_details=("a", "a"), commiter_details=("a", "a"), timestamp=0, message="a")
    assert get_commit_github_url(remote, commit) == f"https://github.com/foo/bar/commit/{sha1}"


def test_get_commit_github_api_url():
    remote = Remote.from_url(url="https://github.com/foo/bar")
    sha1 = "1234567890" * 4
    commit = Commit(sha1=sha1, author_details=("a", "a"), commiter_details=("a", "a"), timestamp=0, message="a")
    assert get_commit_github_api_url(remote, commit) == f"https://api.github.com/repos/foo/bar/commits/{sha1}"
