# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from collections.abc import Generator
from enum import StrEnum
from functools import cached_property
from typing import Self

from msgspec import Struct

from dda.utils.fs import Path
from dda.utils.git.commit import SHA1Hash

FILECHANGES_GIT_DIFF_ARGS = ["diff", "-U0", "--no-color", "--no-prefix", "--no-renames"]


class ChangeType(StrEnum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"

    @classmethod
    def from_github_status(cls, status: str) -> "ChangeType":
        if status == "added":
            return cls.ADDED
        if status == "modified":
            return cls.MODIFIED
        if status == "removed":
            return cls.DELETED

        msg = f"Invalid GitHub change type message: {status}"
        raise ValueError(msg)


class FileChanges(Struct):
    """Represents changes to a single file in a git repository."""

    file: Path
    """The path to the file that was changed."""
    type: ChangeType
    """The type of change that was made to the file: added, modified, or deleted."""

    patch: str
    """
    The patch representing the changes to the file, in unified diff format.
    We only keep the hunk lines (starting with @@) and the lines starting with + or - (no extra context lines).
    This is similar to the format used by the `patch` fields in GitHub's API.

    Example:
    ```diff
    @@ -15,2 +15 @@ if TYPE_CHECKING:
    -    from dda.utils.git.commit import Commit, CommitDetails
    -    from dda.utils.git.commit import SHA1Hash
    +    from dda.utils.git.commit import Commit, CommitDetails, SHA1Hash
    ```
    """

    # TODO: This might be a bit brittle - or we might want to move this to a separate file ?
    @classmethod
    def generate_from_diff_output(cls, diff_output: str | list[str]) -> Generator[Self, None, None]:
        """
        Generate a list of FileChanges from the output of _some_ git diff commands.
        Not all outputs from `git diff` are supported (ex: renames), you should run:
        ```bash
        git diff [dda.utils.git.changeset.FILECHANGES_GIT_DIFF_ARGS] <oldrev> <newrev>
        ```
        Accepts a string or a list of lines.
        """
        if isinstance(diff_output, str):
            diff_output = diff_output.strip().splitlines()

        if len(diff_output) == 0:
            return

        line_iterator = iter(diff_output)

        current_file: Path | None = None
        current_type: ChangeType | None = None
        current_patch_lines: list[str] = []
        iterator_exhausted = False

        try:
            line = next(line_iterator)
            while True:
                # Start processing a new file - the line looks like `diff --git a/<path> b/<path>`
                if not line.startswith("diff --git "):
                    msg = f"Unexpected line in git diff output: {line}"
                    raise ValueError(msg)

                # Go forward until we find the 'old file' line (---)
                while not line.startswith("--- "):
                    try:
                        line = next(line_iterator)
                    except StopIteration:
                        msg = "Unexpected end of git diff output while looking for --- line"
                        raise ValueError(msg)  # noqa: B904

                # When we get here, we are on the --- line
                # It should always be followed by a +++ line
                old_file_line = line

                try:
                    new_file_line = next(line_iterator)
                except StopIteration:
                    msg = "Unexpected end of git diff output while looking for +++ line"
                    raise ValueError(msg)  # noqa: B904
                if not new_file_line.startswith("+++ "):
                    msg = f"Unexpected line in git diff output, expected +++ line: {new_file_line}"
                    raise ValueError(msg)

                old_file_path = old_file_line[4:].strip()
                new_file_path = new_file_line[4:].strip()

                if old_file_path == "/dev/null":
                    current_type = ChangeType.ADDED
                    current_file = Path(new_file_path)
                elif new_file_path == "/dev/null":
                    current_type = ChangeType.DELETED
                    current_file = Path(old_file_path)
                elif old_file_path == new_file_path:
                    current_type = ChangeType.MODIFIED
                    current_file = Path(new_file_path)
                else:
                    msg = f"Unexpected file paths in git diff output: {old_file_path} -> {new_file_path} - this indicates a rename which we do not support"
                    raise ValueError(
                        msg,
                    )

                # Now, we should be at the start of the patch hunks (lines starting with @@)
                line = next(line_iterator)
                if not line.startswith("@@ "):
                    msg = f"Unexpected line in git diff output, expected hunk start: {line}"
                    raise ValueError(msg)
                # Collect hunk lines, i.e. lines starting with @@, +, -, or \ (\ is for the "no newline at end of file" message that can appear)

                while line.startswith(("@@ ", "+", "-", "\\")):
                    current_patch_lines.append(line)
                    try:
                        line = next(line_iterator)
                    except StopIteration:
                        # Just break out of the loop, we will handle yielding below
                        # Set a flag to indicate we reached the end of the iterator
                        iterator_exhausted = True
                        break

                # Yield the file we were building now that we have reached the end of its patch
                yield cls(
                    file=current_file,
                    type=current_type,
                    patch="\n".join(current_patch_lines),
                )
                current_file = None
                current_type = None
                current_patch_lines = []

                if iterator_exhausted:
                    return

        except StopIteration:
            msg = "Unexpected end of git diff output while parsing"
            raise ValueError(msg)  # noqa: B904

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create a FileChanges from a JSON-serializable dictionary."""
        return cls(
            file=Path(data["file"]),
            type=ChangeType.from_github_status(data["change_type"]),
            patch=data["patch"],
        )


# Easier and safer to subclass UserDict than Dict directly
class ChangeSet(dict[Path, FileChanges]):
    """
    Represents a set of changes to files in a git repository.
    This can both be a change between two commits, or the changes in the working directory.

    When considering the changes to the working directory, the untracked files are considered as added files.
    """

    @cached_property
    def added(self) -> set[Path]:
        """List of files that were added."""
        return {change.file for change in self.values() if change.type == ChangeType.ADDED}

    @cached_property
    def modified(self) -> set[Path]:
        """List of files that were modified."""
        return {change.file for change in self.values() if change.type == ChangeType.MODIFIED}

    @cached_property
    def deleted(self) -> set[Path]:
        """List of files that were deleted."""
        return {change.file for change in self.values() if change.type == ChangeType.DELETED}

    @cached_property
    def changed(self) -> set[Path]:
        """List of files that were changed (added, modified, or deleted)."""
        return set(self.keys())

    def add(self, change: FileChanges) -> None:
        """Add a file change to the changeset."""
        self[change.file] = change

    def digest(self) -> SHA1Hash:
        """Compute a hash of the changeset."""
        from hashlib import sha1

        digester = sha1()  # noqa: S324
        for change in sorted(self.values(), key=lambda x: x.file.as_posix()):
            digester.update(change.file.as_posix().encode())
            digester.update(change.type.value.encode())
            digester.update(change.patch.encode())

        return SHA1Hash(digester.hexdigest())

    @classmethod
    def generate_from_diff_output(cls, diff_output: str | list[str]) -> Self:
        """
        Generate a changeset from the output of a git diff command.
        The output should be passed as a string or a list of lines.
        """
        changeset = cls()
        for change in FileChanges.generate_from_diff_output(diff_output):
            changeset.add(change)
        return changeset

    @classmethod
    def from_list(cls, data: list[dict]) -> Self:
        """Create a ChangeSet from a JSON-serializable list."""
        changeset = cls()
        for change in data:
            changeset.add(FileChanges.from_dict(change))
        return changeset
