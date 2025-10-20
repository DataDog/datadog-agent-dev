# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys

import msgspec
import pytest

from dda.types.hooks import dec_hook, enc_hook
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
        encoded_path = msgspec.json.encode(path, enc_hook=enc_hook)
        decoded_path = msgspec.json.decode(encoded_path, type=Path, dec_hook=dec_hook)
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
        encoded_path = msgspec.json.encode(path, enc_hook=enc_hook)
        decoded_path = msgspec.json.decode(encoded_path, type=Path, dec_hook=dec_hook)
        assert decoded_path == path

    @pytest.mark.parametrize(
        ("file", "hashes"),
        [
            (
                "lipsum.txt",
                {
                    "sha256": "e921ca1908b2928951026a4f4aa39b4e0e45faa1ed35c6bec5d0a1172f749b19",
                    "sha512": "39262feb3dddfbfe4fb0f6a7d62cc1e3a5956a8dc9f3f2cfe881ba86883800c66a5854839588193ca3cbf3d7a01f0adf32aafa568d5e8ca83f823070c4c12470",
                    "blake2b": "dd89da4063a1b0725b5f9012a861c4a5dca904a648408d4c6b777b07bdc0294c8736d892ff6a1c0a6e3c58df4c4f6d91682e830f508380333478b11dd1d40e71",
                },
            ),
            (
                "dd_icon_white.svg",
                {
                    "sha256": "846d2ee9685255f043eb26f067bb01b1a1411790f0808b8b137fe2caed271b17",
                    "sha512": "eb712138447228a52af1646ba24fedffa4d847d4759a3481cd233abea65fa82b6daa892d3ecebdfb2cecc62efa63577a68fbf58572e605afcfb99c1b16893b72",
                    "blake2b": "89af50b94a061a28b76e6801a35c202dc1cb50a5d77cbb2f773c46a6834ac111fea717ddfd6758fd21669418fb8dcabc27d5438d5017b9bd614985c399196717",
                },
            ),
            (
                "dd_icon_white.png",
                {
                    "sha256": "b240ea6d9e70afe7a5241386c7d19ac00d1e62322dde29e5a86abd9b90834a42",
                    "sha512": "dcbb45592b3ee64f136c9b81c0f119aeb03eb648ef4b906da48337d518bb9a9b370b420e5a95fdc8952946f08ac3795a4cae4b3b3ac9dfff97aa9c4bc3352ad9",
                    "blake2b": "40c6b509cd6b3efe23038978ea3fedae62ec0fee2ffd264bcf1e64d6270140a145bc5a815a9ff17a82f01cdcc61ac09ad219f47e54c413c41e861f51c883f4da",
                },
            ),
        ],
    )
    def test_hexdigest(self, file, hashes):
        path = Path(__file__).parent / "fixtures" / "hash_files" / file
        algos = hashes.keys()
        for algo in algos:
            # Try with the default buffer size
            digest = path.hexdigest(algorithm=algo)
            assert digest == hashes[algo]

            # Try with another buffer size
            digest = path.hexdigest(algorithm=algo, buffer_size=8192)
            assert digest == hashes[algo]

    def test_hexdigest_invalid_call(self):
        fake_algo = "not_a_real_algo"
        with pytest.raises(
            ValueError,
            match=f"Invalid hashing algorithm `{fake_algo}` requested.",
        ):
            Path().hexdigest(algorithm=fake_algo)

        non_existing_path = Path("/non_existing_file.txt")
        with pytest.raises(FileNotFoundError):
            non_existing_path.hexdigest()

        non_file_path = Path(__file__).parent
        with pytest.raises(IsADirectoryError):
            non_file_path.hexdigest()


def test_temp_directory():
    with temp_directory() as temp_dir:
        assert isinstance(temp_dir, Path)
        assert temp_dir.is_dir()

    assert not temp_dir.exists()
