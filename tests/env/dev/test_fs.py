# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.env.dev.fs import determine_final_copy_target, handle_overwrite, import_from_dir
from dda.utils.fs import Path

pytestmark = [pytest.mark.usefixtures("private_storage")]


@pytest.fixture
def test_files_root():
    """Folder containing test files to be copied."""
    return Path(__file__).parent / "fixtures" / "fs_tests"


@pytest.fixture
def test_source_dir(temp_dir, test_files_root):
    """Directory containing source files (simulates intermediate directory from which we import things)."""
    import shutil

    source_dir = temp_dir / "source_files"
    source_dir.ensure_dir()
    # Copy test files into the source directory
    for item in test_files_root.iterdir():
        if item.is_dir():
            shutil.copytree(str(item), str(source_dir / item.name))
        else:
            shutil.copy2(str(item), str(source_dir / item.name))
    return source_dir


@pytest.fixture
def make_subset_dir(temp_dir, test_source_dir):
    """Factory fixture to create a subset directory with specific source files."""
    import shutil

    def _make_subset(sources: list[str], name: str = "subset") -> Path:
        """Create a directory containing only the specified source files.

        Args:
            sources: List of file/directory names to include in the subset
            name: Name for the subset directory (default: "subset")

        Returns:
            Path to the created subset directory
        """
        subset_dir = temp_dir / name
        subset_dir.ensure_dir()
        for source in sources:
            source_path = test_source_dir / source
            if source_path.is_dir():
                shutil.copytree(str(source_path), str(subset_dir / source))
            else:
                shutil.copy2(str(source_path), str(subset_dir / source))
        return subset_dir

    return _make_subset


@pytest.fixture
def test_target_directory(temp_dir):
    """Directory where the test files should be copied to."""
    res = temp_dir / "test_target"
    res.ensure_dir()
    return res


@pytest.fixture
def prepare_destination(test_target_directory):
    """Factory fixture to prepare a destination path, optionally creating intermediate directories."""

    def _prepare(destination: str = "", *, create_intermediates: bool = True) -> Path:
        """Prepare a destination path for import operations.

        Args:
            destination: Relative destination path (empty string means use root target directory)
            create_intermediates: If True, create intermediate directories

        Returns:
            The prepared destination path
        """
        dest_path = test_target_directory / destination if destination else test_target_directory
        if create_intermediates and destination and not dest_path.exists():
            dest_path.ensure_dir()
        return dest_path

    return _prepare


class TestDetermineFinalCopyTarget:
    def test_file_into_existing_directory(self, temp_dir):
        """When destination is an existing directory, the file should be placed inside it."""
        result = determine_final_copy_target("file.txt", False, temp_dir)
        assert result == temp_dir / "file.txt"

    def test_file_to_nonexistent_path(self, temp_dir):
        """When destination doesn't exist, it should be used as-is (rename case)."""
        nonexistent = temp_dir / "new_name.txt"
        result = determine_final_copy_target("file.txt", False, nonexistent)
        assert result == nonexistent

    def test_directory_into_existing_directory(self, temp_dir):
        """When source is a directory and destination exists, place it inside."""
        result = determine_final_copy_target("mydir", True, temp_dir)
        assert result == temp_dir / "mydir"

    def test_directory_to_nonexistent_path(self, temp_dir):
        """When source is a directory and destination doesn't exist, use destination as-is."""
        nonexistent = temp_dir / "new_dir"
        result = determine_final_copy_target("mydir", True, nonexistent)
        assert result == nonexistent

    def test_directory_to_existing_file_fails(self, temp_dir):
        """Should raise error when trying to overwrite a file with a directory."""
        existing_file = temp_dir / "existing_file.txt"
        existing_file.write_text("content")

        with pytest.raises(ValueError, match="Refusing to overwrite existing file with directory"):
            determine_final_copy_target("mydir", True, existing_file)

    def test_file_to_existing_file(self, temp_dir):
        """When destination is an existing file, it should be used for renaming."""
        existing_file = temp_dir / "existing_file.txt"
        existing_file.write_text("content")

        result = determine_final_copy_target("file.txt", False, existing_file)
        assert result == existing_file


class TestHandleOverwrite:
    """Test the handle_overwrite function."""

    def test_nonexistent_destination_passes(self, test_target_directory):
        """Should pass without errors when destination doesn't exist."""
        nonexistent = test_target_directory / "nonexistent.txt"
        handle_overwrite(nonexistent, force=False)  # Should not raise

    def test_existing_file_without_force_fails(self, test_target_directory):
        """Should raise error when trying to overwrite without force flag."""
        existing_file = test_target_directory / "existing_file.txt"
        existing_file.write_text("content")

        with pytest.raises(ValueError, match="Refusing to overwrite existing file:.* \\(force flag is not set\\)"):
            handle_overwrite(existing_file, force=False)

    def test_existing_file_with_force_succeeds(self, test_target_directory):
        """Should delete the file when force flag is set."""
        existing_file = test_target_directory / "existing_file.txt"
        existing_file.write_text("content")

        handle_overwrite(existing_file, force=True)
        assert not existing_file.exists()

    def test_existing_directory_always_fails(self, test_target_directory):
        """Should raise error when destination is a directory, even with force."""
        existing_dir = test_target_directory / "existing_dir"
        existing_dir.ensure_dir()

        with pytest.raises(ValueError, match="Refusing to overwrite directory"):
            handle_overwrite(existing_dir, force=False)

        with pytest.raises(ValueError, match="Refusing to overwrite directory"):
            handle_overwrite(existing_dir, force=True)


class TestImportFromDir:
    """Test the import_from_dir function with various scenarios."""

    @pytest.mark.parametrize(
        ("sources", "destination", "expected"),
        [
            pytest.param(["file_root.txt"], "", ["file_root.txt"], id="single_file"),
            pytest.param(["file_root.txt"], "file_renamed.txt", ["file_renamed.txt"], id="file_rename"),
            pytest.param(
                ["file_root.txt", "file_root2.txt"], "", ["file_root.txt", "file_root2.txt"], id="multiple_files"
            ),
            pytest.param(
                ["folder1"],
                "",
                ["folder1", "folder1/file_deep1.txt", "folder1/subfolder1", "folder1/subfolder2"],
                id="directory",
            ),
            pytest.param(
                ["file_root.txt", "folder1", "file_root2.txt"],
                "",
                ["file_root.txt", "file_root2.txt", "folder1", "folder1/file_deep1.txt"],
                id="mixed_files_and_directories",
            ),
            pytest.param(
                ["file_root.txt", "folder1"],
                "subdir",
                ["subdir/file_root.txt", "subdir/folder1", "subdir/folder1/file_deep1.txt"],
                id="into_subdir",
            ),
        ],
    )
    def test_import_into_empty_directory(
        self, make_subset_dir, prepare_destination, test_target_directory, sources, destination, expected
    ):
        """Test importing various combinations of files and directories."""
        subset_dir = make_subset_dir(sources)
        destination_path = prepare_destination(destination)

        import_from_dir(subset_dir, destination_path, recursive=True, force=False, mkpath=False)

        for expected_file in expected:
            assert (test_target_directory / expected_file).exists()
            # Verify content for files (not directories)
            file_path = test_target_directory / expected_file
            if file_path.is_file() and "renamed" not in expected_file:
                assert file_path.read_text().strip() == "source"

    class TestRecursiveArg:
        """Tests for the recursive flag."""

        def test_directory_fails_without_flag(self, make_subset_dir, test_target_directory):
            """Should raise error when trying to copy directory without recursive flag."""
            subset_dir = make_subset_dir(["folder1"], name="subset_dir_only")

            with pytest.raises(ValueError, match="Refusing to copy directories as recursive flag is not set"):
                import_from_dir(subset_dir, test_target_directory, recursive=False, force=False, mkpath=False)

        def test_multiple_directories(self, make_subset_dir, test_target_directory):
            """Should successfully copy multiple directories with recursive flag."""
            subset_dir = make_subset_dir(["folder1", "folder2"], name="subset_multi_dir")

            import_from_dir(subset_dir, test_target_directory, recursive=True, force=False, mkpath=False)

            assert (test_target_directory / "folder1").exists()
            assert (test_target_directory / "folder1" / "file_deep1.txt").exists()
            assert (test_target_directory / "folder2").exists()
            assert (test_target_directory / "folder2" / "file_deep2.txt").exists()

    class TestForceArg:
        """Tests for the force flag."""

        def test_overwrite_fails_without_flag(self, make_subset_dir, test_target_directory):
            """Should raise error when trying to overwrite without force flag."""
            subset_dir = make_subset_dir(["file_root.txt"], name="subset_single")

            # Create existing file at destination
            existing_file = test_target_directory / "file_root.txt"
            existing_file.write_text("existing content")

            with pytest.raises(ValueError, match="Refusing to overwrite existing file:.* \\(force flag is not set\\)"):
                import_from_dir(subset_dir, test_target_directory, recursive=False, force=False, mkpath=False)

            assert existing_file.read_text() == "existing content"

        def test_overwrite_succeeds_with_flag(self, make_subset_dir, test_target_directory):
            """Should successfully overwrite files when force flag is set."""
            subset_dir = make_subset_dir(["file_root.txt"], name="subset_single_overwrite")

            # Create existing file at destination
            existing_file = test_target_directory / "file_root.txt"
            existing_file.write_text("existing content")

            import_from_dir(subset_dir, test_target_directory, recursive=False, force=True, mkpath=False)

            assert existing_file.read_text().strip() == "source"

    class TestMkpathArg:
        """Tests for the mkpath flag."""

        def test_nonexistent_path_fails_without_mkpath(self, make_subset_dir, test_target_directory):
            """Should raise error when destination doesn't exist and mkpath is False."""
            subset_dir = make_subset_dir(["file_root.txt"], name="subset_mkpath_fail")
            nonexistent_dir = test_target_directory / "nonexistent" / "deep" / "path"

            with pytest.raises(FileNotFoundError):
                import_from_dir(subset_dir, nonexistent_dir, recursive=False, force=False, mkpath=False)

        def test_nonexistent_path_succeeds_with_mkpath(self, make_subset_dir, test_target_directory):
            """Should create intermediate directories when mkpath is True."""
            subset_dir = make_subset_dir(["file_root.txt"], name="subset_mkpath_success")
            nonexistent_dir = test_target_directory / "nonexistent" / "deep" / "path"

            import_from_dir(subset_dir, nonexistent_dir, recursive=False, force=False, mkpath=True)

            assert nonexistent_dir.exists()
            assert (nonexistent_dir / "file_root.txt").exists()
            assert (nonexistent_dir / "file_root.txt").read_text().strip() == "source"

    class TestExistingElements:
        """Tests for importing to a directory that already contains stuff."""

        def test_directory_to_existing_directory(self, make_subset_dir, test_target_directory):
            """Should place source directory inside existing directory with stuff in it."""
            subset_dir = make_subset_dir(["folder1"], name="subset_into_existing")

            (test_target_directory / "existing_dir").ensure_dir()
            (test_target_directory / "existing_dir" / "existing_file.txt").write_text("existing content")

            import_from_dir(
                subset_dir, test_target_directory / "existing_dir", recursive=True, force=False, mkpath=False
            )

            assert (test_target_directory / "existing_dir" / "folder1").exists()
            assert (test_target_directory / "existing_dir" / "folder1" / "file_deep1.txt").exists()

        def test_directory_to_existing_file_fails(self, make_subset_dir, test_target_directory):
            """Should raise error when trying to place directory where a file exists."""
            subset_dir = make_subset_dir(["folder1"], name="subset_dir_to_file")

            existing_file = test_target_directory / "some_file.txt"
            existing_file.write_text("existing content")

            with pytest.raises(ValueError, match="Refusing to overwrite existing file with directory"):
                import_from_dir(subset_dir, existing_file, recursive=True, force=False, mkpath=False)
