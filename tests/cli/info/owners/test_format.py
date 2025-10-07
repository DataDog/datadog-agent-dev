from dda.cli.info.owners.format import format_path_for_codeowners
from dda.utils.fs import Path


def test_format_path_for_codeowners(temp_dir, create_temp_file_or_dir):
    with temp_dir.as_cwd():
        # Test 1: Subpath is a file
        create_temp_file_or_dir(temp_dir / "some" / "path", force_file=True)

        assert format_path_for_codeowners(Path("some/path")) == "some/path"
        assert format_path_for_codeowners(Path("some/path/")) == "some/path"
        assert format_path_for_codeowners(Path("./some/path")) == "some/path"

        # Test 2: Subpath is a directory
        create_temp_file_or_dir(temp_dir / "some" / "path2", force_file=False)
        assert format_path_for_codeowners(Path("some/path2/")) == "some/path2/"
        assert format_path_for_codeowners(Path("some/path2")) == "some/path2/"
        assert format_path_for_codeowners(Path("./some/path2")) == "some/path2/"

        # Test 2: Subpath is a directory with an extension
        create_temp_file_or_dir(temp_dir / "some" / "path.ext" / "file.txt", force_file=True)

        assert format_path_for_codeowners(Path("some/path.ext/")) == "some/path.ext/"
        assert format_path_for_codeowners(Path("some/path.ext/file.txt")) == "some/path.ext/file.txt"
