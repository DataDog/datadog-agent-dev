# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.utils.git.commit import Commit
from dda.utils.git.sha1hash import SHA1Hash


def test_commit():
    commit = Commit(org="foo", repo="bar", sha1=SHA1Hash("82ee754ca931816902ac7e6e38f66a51e65912f9"))
    assert commit.org == "foo"
    assert commit.repo == "bar"
    assert commit.sha1 == "82ee754ca931816902ac7e6e38f66a51e65912f9"
    assert commit.full_repo == "foo/bar"
    assert commit.github_url == "https://github.com/foo/bar/commit/82ee754ca931816902ac7e6e38f66a51e65912f9"
    assert (
        commit.github_api_url == "https://api.github.com/repos/foo/bar/commits/82ee754ca931816902ac7e6e38f66a51e65912f9"
    )


# Already tested in tools/test_git.py
# def test_head():
#     pass
