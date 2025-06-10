# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys

import pytest

from dda.utils.container.model import Mount


class TestMount:
    def test_bind_without_source(self):
        with pytest.raises(ValueError, match="source is required for bind mounts"):
            Mount(type="bind", path="target")

    def test_anonymous_volume(self):
        mount = Mount(type="volume", path="target")
        assert mount.as_csv() == "type=volume,dst=target"

    def test_named_volume(self):
        mount = Mount(type="volume", path="target", source="volume_name")
        assert mount.as_csv() == "type=volume,src=volume_name,dst=target"

    def test_named_volume_with_options(self):
        mount = Mount(type="volume", path="target", source="volume_name", volume_options={"foo": "bar", "baz": "qux"})
        assert mount.as_csv() == "type=volume,src=volume_name,dst=target,volume-opt=foo=bar,volume-opt=baz=qux"

    def test_read_only(self):
        mount = Mount(type="bind", path="target", source="source", read_only=True)
        assert mount.as_csv() == "type=bind,src=source,dst=target,ro"

    def test_quoting(self):
        mount = Mount(type="bind", path="target", source="foo,bar")
        assert mount.as_csv() == 'type=bind,"src=foo,bar",dst=target'

    def test_quoting_with_escaping(self):
        mount = Mount(type="bind", path='foo"bar', source='foo,bar"baz')
        assert mount.as_csv() == 'type=bind,"src=foo,bar""baz","dst=foo""bar"'

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_bind_mount_on_windows(self):
        mount = Mount(type="bind", path="target", source="C:\\Users\\foo")
        assert mount.as_csv() == "type=bind,src=/c/Users/foo,dst=target"
