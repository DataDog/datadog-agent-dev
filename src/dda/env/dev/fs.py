# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.utils.fs import Path


def determine_final_copy_target(source_name: str, source_is_dir: bool, destination_spec: Path) -> Path:  # noqa: FBT001
    """
    Determines the final target for a copy operation, given a destination specification and some details about the source.
    For example:
    - f("file.txt", False, "/tmp/some-dir") -> "/tmp/some-dir/file.txt" (move into directory)
    - f("file.txt", False, "/tmp/new-file.txt") -> "/tmp/new-file.txt" (rename file)
    - f("some-dir", True, "/tmp/some-dir") -> "/tmp/some-dir/some-dir" (move directory into directory)

    Parameters:
    - source_name: The name of the source file or directory. The source is usually inside the env filesystem, not the host.
    - source_is_dir: Whether the source is a directory.
    - destination_spec: The destination specification, which can be a directory or a file. The destination is usually on the host filesystem.

    Returns:
    - The final target path.
    """

    if destination_spec.is_dir():
        # The destination exists and is a directory or a symlink to one
        # Always move the source inside it
        # TODO: Add a check if destination_spec / source.name is an already-existing file or directory
        # Currently shutil.move will fail with an ugly error message when we eventually call it
        return destination_spec / source_name

    if destination_spec.is_file():
        # The destination exists and is a file
        if source_is_dir:
            # Never overwrite a file with a directory
            msg = f"Refusing to overwrite existing file with directory: {destination_spec}"
            raise ValueError(msg)
        # Source and destination are both files - rename
        return destination_spec

    # The destination does not exist, assume we want it exactly there
    return destination_spec


def handle_overwrite(dest: Path, *, force: bool) -> None:
    if not dest.exists():
        return

    if dest.is_dir():
        msg = f"Refusing to overwrite directory {dest}."
        raise ValueError(msg)

    if not force:
        msg = f"Refusing to overwrite existing file: {dest} (force flag is not set)."
        raise ValueError(msg)

    dest.unlink()


def import_from_dir(source_dir: Path, destination_spec: Path, *, recursive: bool, force: bool, mkpath: bool) -> None:
    """
    Import files and directories from a given directory into a destination directory on the "host" filesystem.
    "Host" in this context refers to the environment `dda` is being executed in: if that is inside of a dev env, then we mean the dev env's file system.
    """
    from shutil import move

    if mkpath:
        destination_spec.ensure_dir()

    for element in source_dir.iterdir():
        if not recursive and element.is_dir():
            msg = "Refusing to copy directories as recursive flag is not set"
            raise ValueError(msg)

        final_target = determine_final_copy_target(element.name, element.is_dir(), destination_spec)
        handle_overwrite(final_target, force=force)
        move(element, final_target)
