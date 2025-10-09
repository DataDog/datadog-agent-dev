from dda.cli.info.owners.format import format_path_for_codeowners
from dda.utils.fs import Path


def test_format_path_for_codeowners():
    with (Path(__file__).parent / "fixtures" / "test_format").as_cwd():
        # Test 1: Subpath is a file
        assert format_path_for_codeowners(Path("some/path")) == "some/path"
        assert format_path_for_codeowners(Path("some/path/")) == "some/path"
        assert format_path_for_codeowners(Path("./some/path")) == "some/path"

        # Test 2: Subpath is a directory
        assert format_path_for_codeowners(Path("some/path2/")) == "some/path2/"
        assert format_path_for_codeowners(Path("some/path2")) == "some/path2/"
        assert format_path_for_codeowners(Path("./some/path2")) == "some/path2/"

        # Test 2: Subpath is a directory with an extension
        assert format_path_for_codeowners(Path("some/path.ext/")) == "some/path.ext/"
        assert format_path_for_codeowners(Path("some/path.ext/file.txt")) == "some/path.ext/file.txt"
