# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.utils.git.remote import Remote


class TestRemoteClass:
    @pytest.mark.parametrize(
        ("url", "full_repo", "org", "repo", "protocol", "hostname", "port", "username"),
        [
            # URI Style
            # Test different protocols
            ("https://github.com/foo/bar.git", "foo/bar", "foo", "bar", "https", "github.com", None, None),
            ("http://github.com/foo/bar.git", "foo/bar", "foo", "bar", "http", "github.com", None, None),
            ("ssh://github.com/foo/bar.git", "foo/bar", "foo", "bar", "ssh", "github.com", None, None),
            ("git://github.com/foo/bar.git", "foo/bar", "foo", "bar", "git", "github.com", None, None),
            ("file://github.com/foo/bar.git", "foo/bar", "foo", "bar", "file", "github.com", None, None),
            ("rsync://github.com/foo/bar.git", "foo/bar", "foo", "bar", "rsync", "github.com", None, None),
            # Test without .git suffix
            ("https://github.com/foo/bar", "foo/bar", "foo", "bar", "https", "github.com", None, None),
            # Test with port and username and both
            ("ssh://user@github.com:443/foo/bar", "foo/bar", "foo", "bar", "ssh", "github.com", 443, "user"),
            ("ssh://user@github.com/foo/bar.git", "foo/bar", "foo", "bar", "ssh", "github.com", None, "user"),
            ("rsync://github.com:2323/foo/bar.git", "foo/bar", "foo", "bar", "rsync", "github.com", 2323, None),
            # Test with a different host
            ("https://gitlab.com/foo/bar.git", "foo/bar", "foo", "bar", "https", "gitlab.com", None, None),
            ("ssh://user@gitlab.com:232/foo/bar", "foo/bar", "foo", "bar", "ssh", "gitlab.com", 232, "user"),
            # SCP-style SSH
            ("git@github.com:foo/bar.git", "foo/bar", "foo", "bar", "ssh", "github.com", None, "git"),
            ("git@github.com:foo/bar", "foo/bar", "foo", "bar", "ssh", "github.com", None, "git"),
            ("git@gitlab.com:foo/bar.git", "foo/bar", "foo", "bar", "ssh", "gitlab.com", None, "git"),
            ("git@gitlab.com:foo/bar", "foo/bar", "foo", "bar", "ssh", "gitlab.com", None, "git"),
        ],
    )
    def test_basic(self, url, full_repo, org, repo, protocol, hostname, port, username):
        remote = Remote(url=url)
        assert remote.url == url
        assert remote.full_repo == full_repo
        assert remote.org == org
        assert remote.repo == repo
        assert remote.protocol == protocol
        assert remote.hostname == hostname
        assert remote.port == port
        assert remote.username == username
