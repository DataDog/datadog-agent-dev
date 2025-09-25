# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.utils.git.remote import Remote


class TestRemoteClass:
    @pytest.mark.parametrize(
        ("url", "protocol", "authority", "path", "username", "host", "port"),
        [
            # URI Style
            # Test different protocols
            ("https://github.com/foo/bar.git", "https", "github.com", "foo/bar", None, "github.com", None),
            ("http://github.com/foo/bar.git", "http", "github.com", "foo/bar", None, "github.com", None),
            ("ssh://github.com/foo/bar.git", "ssh", "github.com", "foo/bar", None, "github.com", None),
            ("git://github.com/foo/bar.git", "git", "github.com", "foo/bar", None, "github.com", None),
            ("file://github.com/foo/bar.git", "file", "github.com", "foo/bar", None, "github.com", None),
            ("rsync://github.com/foo/bar.git", "rsync", "github.com", "foo/bar", None, "github.com", None),
            # Test without .git suffix
            ("https://github.com/foo/bar", "https", "github.com", "foo/bar", None, "github.com", None),
            # Test with port and username and both
            ("ssh://user@github.com:443/foo/bar", "ssh", "user@github.com:443", "foo/bar", "user", "github.com", 443),
            ("ssh://user@github.com/foo/bar.git", "ssh", "user@github.com", "foo/bar", "user", "github.com", None),
            ("rsync://github.com:2323/foo/bar.git", "rsync", "github.com:2323", "foo/bar", None, "github.com", 2323),
            # Test with a different host
            ("https://gitlab.com/foo/bar.git", "https", "gitlab.com", "foo/bar", None, "gitlab.com", None),
            ("ssh://user@gitlab.com:232/foo/bar", "ssh", "user@gitlab.com:232", "foo/bar", "user", "gitlab.com", 232),
            # RCP Style
            ("git@github.com:foo/bar.git", "ssh", "git@github.com", "foo/bar", "git", "github.com", None),
            ("git@github.com:foo/bar", "ssh", "git@github.com", "foo/bar", "git", "github.com", None),
            ("git@gitlab.com:foo/bar.git", "ssh", "git@gitlab.com", "foo/bar", "git", "gitlab.com", None),
            ("git@gitlab.com:foo/bar", "ssh", "git@gitlab.com", "foo/bar", "git", "gitlab.com", None),
        ],
    )
    def test_basic(self, url, protocol, authority, path, username, host, port):
        remote = Remote.from_url(url=url)
        assert remote.url == url
        assert remote.protocol == protocol
        assert remote.authority == authority
        assert remote.path == path
        assert remote.username == username
        assert remote.host == host
        assert remote.port == port
