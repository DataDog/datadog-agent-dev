# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.utils.git.remote import HTTPSRemote, Remote, SSHRemote


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
