# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from enum import StrEnum
from functools import cached_property
from itertools import chain
from types import MappingProxyType
from typing import TYPE_CHECKING, Self

from msgspec import Struct, convert, to_builtins

from dda.types.hooks import dec_hook, enc_hook, register_type_hooks
from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Iterable


class ChangeType(StrEnum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"


class ChangedFile(Struct, frozen=True):
    """Represents changes to a single file in a git repository."""

    path: Path
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


class ChangeSet:  # noqa: PLW1641
    """
    Represents a set of changes to files in a git repository.
    This can both be a change between two commits, or the changes in the working directory.

    When considering the changes to the working directory, the untracked files are considered as added files.
    """

    def __init__(self, changed_files: Iterable[ChangedFile]) -> None:
        self.__changed = MappingProxyType({str(c.path): c for c in changed_files})
        self.__files = tuple(self.__changed.values())

    @property
    def paths(self) -> MappingProxyType[str, ChangedFile]:
        return self.__changed

    @property
    def files(self) -> Iterable[ChangedFile]:
        return self.__files

    @property
    def added(self) -> MappingProxyType[str, ChangedFile]:
        """Set of files that were added."""
        return self.__change_types[ChangeType.ADDED]

    @property
    def modified(self) -> MappingProxyType[str, ChangedFile]:
        """Set of files that were modified."""
        return self.__change_types[ChangeType.MODIFIED]

    @property
    def deleted(self) -> MappingProxyType[str, ChangedFile]:
        """Set of files that were deleted."""
        return self.__change_types[ChangeType.DELETED]

    def digest(self) -> str:
        """Compute a hash of the changeset."""
        from hashlib import sha256

        digester = sha256()
        for change in sorted(self.files, key=lambda cf: cf.path):
            digester.update(change.path.as_posix().encode())
            digester.update(change.type.value.encode())
            digester.update(change.patch.encode())

        return str(digester.hexdigest())

    @classmethod
    def from_patches(cls, diff_output: str | list[str]) -> Self:
        """
        Generate a ChangeSet from the output of _some_ git diff commands.
        Not all outputs from `git diff` are supported (ex: renames).
        """
        import re

        if isinstance(diff_output, list):
            diff_output = "\n".join(diff_output)

        changes = []
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
            changes.append(ChangedFile(path=current_file, type=current_type, binary=binary, patch=patch))
        return cls(changes)

    def __or__(self, other: Self) -> Self:
        return type(self)(chain(self.files, other.files))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ChangeSet) and self.paths == other.paths

    def __len__(self) -> int:
        return len(self.__files)

    def __bool__(self) -> bool:
        return bool(self.__files)

    @cached_property
    def __change_types(self) -> dict[ChangeType, MappingProxyType[str, ChangedFile]]:
        changes: dict[ChangeType, dict[str, ChangedFile]] = {}
        for change in self.files:
            changes.setdefault(change.type, {})[str(change.path)] = change

        return {change_type: MappingProxyType(paths) for change_type, paths in changes.items()}


def _determine_change_type(before_filename: str, after_filename: str) -> ChangeType:
    if before_filename == after_filename:
        return ChangeType.MODIFIED
    if before_filename == "/dev/null":
        return ChangeType.ADDED
    if after_filename == "/dev/null":
        return ChangeType.DELETED

    msg = f"Unexpected file paths in git diff output: {before_filename} -> {after_filename} - this indicates a rename which we do not support"
    raise ValueError(msg)


register_type_hooks(
    ChangeSet,
    encode=lambda obj: to_builtins(obj.files, enc_hook=enc_hook),
    decode=lambda obj: ChangeSet(convert(cf, ChangedFile, dec_hook=dec_hook) for cf in obj),
)
