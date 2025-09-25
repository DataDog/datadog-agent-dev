# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from enum import StrEnum
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Self

from msgspec import Struct

from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Generator, ItemsView, Iterable, Iterator, KeysView, ValuesView


class ChangeType(StrEnum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"


class ChangedFile(Struct, frozen=True):
    """Represents changes to a single file in a git repository."""

    file: Path
    """The path to the file that was changed."""
    type: ChangeType
    """The type of change that was made to the file: added, modified, or deleted."""

    binary: bool
    """Whether the changed file was a binary file."""

    patch: str
    """
    The patch representing the changes to the file, in unified diff format.
    We only keep the hunk lines (starting with @@) and the lines starting with + or - (no extra context lines).
    This is similar to the format used by the `patch` fields in GitHub's API.

    Example:
    ```diff
    @@ -15,1 +15 @@ if TYPE_CHECKING:
    -    from dda.utils.git.commit import Commit
    -    from dda.utils.git.commit import CommitDetails
    +    from dda.utils.git.commit import Commit, CommitDetails
    ```
    """

    # TODO: This might be a bit brittle - or we might want to move this to a separate file ?
    @classmethod
    def generate_from_diff_output(cls, diff_output: str | list[str]) -> Generator[Self, None, None]:
        """
        Generate a list of FileChanges from the output of _some_ git diff commands.
        Not all outputs from `git diff` are supported (ex: renames), see set of args in [Git._capture_diff_lines](dda.tools.git.Git._capture_diff_lines) method.
        """
        import re

        if isinstance(diff_output, list):
            diff_output = "\n".join(diff_output)

        for modification in re.split(r"^diff --git ", diff_output, flags=re.MULTILINE):
            if not modification:
                continue

            # Extract metadata. It can be in two formats, depending on if the file is a binary file or not.

            # Binary files:
            # (new file mode 100644) - not always present
            # index 0000000000..089fd64579
            # Binary files /dev/null and foo/archive.tar.gz differ

            # Regular files:
            # (new file mode 100644) - not always present
            # index 0000000000..089fd64579
            # --- a/file
            # +++ b/file
            # @@ ... @@ (start of hunks)
            sep = "@@ "
            metadata, *blocks = re.split(rf"^{sep}", modification, flags=re.MULTILINE)
            metadata_lines = metadata.strip().splitlines()

            # Determine if the file is a binary file
            binary = metadata_lines[-1].startswith("Binary files ")

            # Extract old and new file paths
            if binary:
                line = metadata_lines[-1].removeprefix("Binary files ")
                # This might raise an error if one of the files contains the string " and "
                before_filename, after_filename = line.split(" and ")
            else:
                before_filename = metadata_lines[-2].split(maxsplit=1)[1]
                after_filename = metadata_lines[-1].split(maxsplit=1)[1]

            # Determine changetype
            current_type = _determine_change_type(before_filename, after_filename)
            current_file = Path(after_filename) if current_type == ChangeType.ADDED else Path(before_filename)

            # Strip every "block" and add the missing separator
            patch = "" if binary else "\n".join([sep + block.strip() for block in blocks]).strip()
            yield cls(file=current_file, type=current_type, binary=binary, patch=patch)

    @classmethod
    def enc_hook(cls, obj: Any) -> Any:
        # Only unsupported objects are Path objects
        return Path.enc_hook(obj)

    @classmethod
    def dec_hook(cls, obj_type: type, obj: Any) -> Any:  # type: ignore[valid-type]
        # Only unsupported objects are Path objects
        return Path.dec_hook(obj_type, obj)


# Need dict=True so that cached_property can be used
class ChangeSet(Struct, dict=True, frozen=True):
    changes: MappingProxyType[Path, ChangedFile]

    """
    Represents a set of changes to files in a git repository.
    This can both be a change between two commits, or the changes in the working directory.

    When considering the changes to the working directory, the untracked files are considered as added files.
    """

    def keys(self) -> KeysView[Path]:
        return self.changes.keys()

    def values(self) -> ValuesView[ChangedFile]:
        return self.changes.values()

    def items(self) -> ItemsView[Path, ChangedFile]:
        return self.changes.items()

    def __getitem__(self, key: Path) -> ChangedFile:
        return self.changes[key]

    def __contains__(self, key: Path) -> bool:
        return key in self.changes

    def __len__(self) -> int:
        return len(self.changes)

    def __iter__(self) -> Iterator[Path]:
        return iter(self.changes.keys())

    def __or__(self, other: Self) -> Self:
        return self.from_iter(list(self.values()) + list(other.values()))

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

    def digest(self) -> str:
        """Compute a hash of the changeset."""
        from hashlib import sha256

        digester = sha256()
        for change in sorted(self.values(), key=lambda x: x.file.as_posix()):
            digester.update(change.file.as_posix().encode())
            digester.update(change.type.value.encode())
            digester.update(change.patch.encode())

        return str(digester.hexdigest())

    @classmethod
    def from_iter(cls, data: Iterable[ChangedFile]) -> Self:
        """Create a ChangeSet from an iterable of FileChanges."""
        items = {change.file: change for change in data}
        return cls(changes=MappingProxyType(items))

    @classmethod
    def generate_from_diff_output(cls, diff_output: str | list[str]) -> Self:
        """
        Generate a changeset from the output of a git diff command.
        The output should be passed as a string or a list of lines.
        """
        return cls.from_iter(ChangedFile.generate_from_diff_output(diff_output))

    @classmethod
    def enc_hook(cls, obj: Any) -> Any:
        # Encode MappingProxy objects as dicts
        if isinstance(obj, MappingProxyType):
            return dict(obj)

        if isinstance(obj, Path):
            return Path.enc_hook(obj)

        msg = f"Cannot encode object of type {type(obj)}"
        raise NotImplementedError(msg)

    @classmethod
    def dec_hook(cls, obj_type: type, obj: Any) -> Any:
        from msgspec import convert

        changes_type = MappingProxyType[Path, ChangedFile]

        if obj_type == changes_type:
            # Since the dict decode logic from msgspec is not called here we have to manually decode the keys and values
            decoded_obj = {}
            for key, value in obj.items():
                decoded_key = Path.dec_hook(Path, key)
                decoded_value = convert(value, ChangedFile, dec_hook=cls.dec_hook)
                decoded_obj[decoded_key] = decoded_value
            return MappingProxyType(decoded_obj)

        if obj_type is Path:
            return Path.dec_hook(obj_type, obj)

        msg = f"Cannot decode object of type {obj_type}"
        raise NotImplementedError(msg)


def _determine_change_type(before_filename: str, after_filename: str) -> ChangeType:
    if before_filename == after_filename:
        return ChangeType.MODIFIED
    if before_filename == "/dev/null":
        return ChangeType.ADDED
    if after_filename == "/dev/null":
        return ChangeType.DELETED

    msg = f"Unexpected file paths in git diff output: {before_filename} -> {after_filename} - this indicates a rename which we do not support"
    raise ValueError(msg)
