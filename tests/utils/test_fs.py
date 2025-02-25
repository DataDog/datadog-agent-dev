# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys

import pytest

from dda.utils.fs import Path, temp_directory


class TestPath:
    def test_ensure_dir(self, tmp_path):
        path = Path(tmp_path, "foo")
        path.ensure_dir()

        assert path.is_dir()

    def test_as_cwd(self, tmp_path):
        origin = os.getcwd()

        with Path(tmp_path).as_cwd():
            assert os.getcwd() == str(tmp_path)

        assert os.getcwd() == origin

    @pytest.mark.skipif(sys.platform not in {"win32", "darwin"}, reason="Requires case-insensitive filesystem")
    def test_id(self):
        path = Path()

        assert path.id == Path(str(path).upper()).id


def test_temp_directory():
    with temp_directory() as temp_dir:
        assert isinstance(temp_dir, Path)
        assert temp_dir.is_dir()

    assert not temp_dir.exists()
