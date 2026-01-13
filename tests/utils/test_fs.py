# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys

import msgspec
import pytest

from dda.types.hooks import dec_hook, enc_hook
from dda.utils.fs import Path, cp_r, temp_directory, temp_file


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
        ("data", "hashes"),
        [
            (
                b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. In aliquet felis in pretium aliquet. Ut ac laoreet quam. Vivamus velit.",
                {
                    "sha256": "cfa2679987c09a6a650119bb403b7409097dde137fd5d6c5b73e1887ce2b1fa9",
                    "sha512": "51799af49d7e298ae8ecc9d3cb8494ce1798bc30b8ec00bd94ba9b4dcdf1cf44fb3adf2ff4046543a50b0c8d480813895712b53561803dd482037d670ee92dbb",
                    "blake2b": "4398d6c895645672abe343c4bcaa283adb7e35e534b1dc164a2426040ca74b4b285b5847f5fa86ce51aa84159a587cc5332cbeb8ceaa3b98c4f6fccdbc36df55",
                },
            ),
            (
                b"Etiam eget imperdiet enim, vel blandit mauris. Cras dapibus nam.",
                {
                    "sha256": "ef7f1b043a2b91c2900ead0091f1ac715a8e97f5bf4508cff3738ac11b711f03",
                    "sha512": "21907a7f2c887c871a38919154916a81e2f3bb75dd26bbcde2d12c4c3d2c82eb83f94446196fcbdd35cad5bd9e17f3efafb2e2300949b0d93e18b5c54df1ab56",
                    "blake2b": "3815deec2d01e0a7ca59fb3c7782f668d10ff04b3d0c3973db1f934f18d92ec24c3fc2aead937736144f0e65d29440520de68ce75d88e258db72b1062edb825c",
                },
            ),
            (
                b"Phasellus congue commodo erat quis eleifend. Nulla semper velit eget mauris ultricies laoreet.\n Sed orci tellus, venenatis vitae egestas vel, vehicula eget odio.",
                {
                    "sha256": "4ca6c0ca071e0cfdab3f6aeea99f852d6b9e2981409ffffa7a8f88b1e951c605",
                    "sha512": "c357c4eb2c8093774a807393fc19dcd980d8335c5d6e1d8b98bc1b8be2002a4c3f0d19b78f5d08290f8ec30f22951d3bff72c0ae8f0bfbe88429f9234ecb49d9",
                    "blake2b": "12edd771bf10e018bf31896985a4ce36941127d80d1e738ad712e0e4717c04deb0fa98f1dad02126e903f370019d9168041240722dc821386f5ff4efce36dd63",
                },
            ),
        ],
    )
    def test_hexdigest(self, data, hashes):
        algos = hashes.keys()
        with temp_file(suffix=".txt") as path:
            path.write_atomic(data, "wb")
            for algo in algos:
                # Try with the default buffer size
                digest = path.hexdigest(algorithm=algo)
                assert digest == hashes[algo]

                # Try with another buffer size
                digest = path.hexdigest(algorithm=algo, buffer_size=32)
                assert digest == hashes[algo]

    def test_hexdigest_invalid_call(self, temp_dir):
        fake_algo = "not_a_real_algo"
        with pytest.raises(
            ValueError,
            match=f"Invalid hashing algorithm `{fake_algo}` requested.",
        ):
            Path().hexdigest(algorithm=fake_algo)

        non_existing_path = Path("/non_existing_file.txt")
        with pytest.raises(FileNotFoundError):
            non_existing_path.hexdigest()

        non_file_path = temp_dir
        with pytest.raises((IsADirectoryError, PermissionError)):
            non_file_path.hexdigest()


def test_temp_directory():
    with temp_directory() as temp_dir:
        assert isinstance(temp_dir, Path)
        assert temp_dir.is_dir()

    assert not temp_dir.exists()


@pytest.fixture
def test_files_root():
    # Folder containing test files to be copied
    # Stands in for an arbitrary path on the source filesystem
    return Path(__file__).parent.parent / "fixtures" / "import_export_tests" / "examples"


def _check_path_equality(path1: Path, path2: Path) -> None:
    if path1.is_file():
        assert path2.is_file()
        assert path1.read_text() == path2.read_text()
        return

    if path1.is_dir():
        assert path2.is_dir()
        assert {p.name for p in path1.iterdir()} == {p.name for p in path2.iterdir()}
        return

    # Here destination must be nonexistent
    assert not path1.exists()
    assert not path2.exists()


class TestCpR:
    """Test the cp_r function to verify it behaves like 'cp -r'."""

    @pytest.mark.parametrize(
        "source",
        [
            pytest.param("file_root.txt", id="single_file"),
            pytest.param("folder1", id="directory"),
            pytest.param("folder2", id="deep_directory"),
        ],
    )
    def test_destination_not_exist(self, temp_dir, app, test_files_root, source):
        """Test behavior match when the destination does not exist"""
        source = test_files_root / source
        destination = temp_dir / "destination_not_exist"
        assert not destination.exists()
        cp_r(source, destination)

        destination2 = temp_dir / "destination_not_exist2"
        assert not destination2.exists()
        app.subprocess.run(["cp", "-r", str(source), str(destination2)])

        # Check destination and destination2 are the same
        _check_path_equality(destination, destination2)

    @pytest.mark.parametrize(
        "source",
        [
            pytest.param("file_root.txt", id="single_file"),
            pytest.param("folder1", id="directory"),
            pytest.param("folder2", id="deep_directory"),
        ],
    )
    def test_destination_is_directory(self, temp_dir, app, test_files_root, source):
        """Test behavior match when the destination is a directory"""
        source = test_files_root / source
        destination = temp_dir / "destination_is_directory"
        destination.mkdir()
        cp_r(source, destination)

        destination2 = temp_dir / "destination_not_exist2"
        destination2.mkdir()
        app.subprocess.run(["cp", "-r", str(source), str(destination2)])

        # Check destination and destination2 are the same
        _check_path_equality(destination, destination2)

    @pytest.mark.parametrize(
        ("source", "should_error"),
        [
            pytest.param("file_root.txt", False, id="single_file"),
            pytest.param("folder1", True, id="directory"),  # cp -r on a directory to a file should error
            pytest.param("folder2", True, id="deep_directory"),
        ],
    )
    def test_destination_is_file(self, temp_dir, app, test_files_root, source, should_error):
        """Test behavior match when the destination is an existing file"""
        source = test_files_root / source
        destination = temp_dir / "destination_is_file"
        destination.write_text("existing content")
        if should_error:
            with pytest.raises(FileExistsError):
                cp_r(source, destination)
            return  # Don't bother running cp -r if it should error
        cp_r(source, destination)

        destination2 = temp_dir / "destination_is_file2"
        destination2.write_text("existing content2")
        app.subprocess.run(["cp", "-r", str(source), str(destination2)])
        # Check destination and destination2 are the same
        _check_path_equality(destination, destination2)
