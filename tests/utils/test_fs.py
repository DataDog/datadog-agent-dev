# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys

import msgspec
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

    @pytest.mark.requires_unix
    @pytest.mark.parametrize(
        "path_str",
        ["foo", "foo/bar", "foo/bar/", "foo/bar/baz.txt", ".", "~/foo/bar", "foo/bar/../bar", "/", "/foo/bar"],
    )
    def test_encode_decode_unix(self, path_str):
        path = Path(path_str)
        encoded_path = msgspec.json.encode(path, enc_hook=Path.enc_hook)
        decoded_path = msgspec.json.decode(encoded_path, type=Path, dec_hook=Path.dec_hook)
        assert decoded_path == path

    @pytest.mark.requires_windows
    @pytest.mark.parametrize(
        "path_str",
        [
            "foo",
            "foo\\bar",
            "foo\\bar\\",
            "foo\\bar\\baz.txt",
            ".",
            "~\\foo\\bar",
            "foo\\bar\\..\\bar",
            "C:\\",
            "C:\\foo\\bar",
        ],
    )
    def test_encode_decode_windows(self, path_str):
        path = Path(path_str)
        encoded_path = msgspec.json.encode(path, enc_hook=Path.enc_hook)
        decoded_path = msgspec.json.decode(encoded_path, type=Path, dec_hook=Path.dec_hook)
        assert decoded_path == path


def test_temp_directory():
    with temp_directory() as temp_dir:
        assert isinstance(temp_dir, Path)
        assert temp_dir.is_dir()

    assert not temp_dir.exists()
