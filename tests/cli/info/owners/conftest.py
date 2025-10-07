# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from os import sep
from typing import TYPE_CHECKING

import pytest

from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Iterable


# We prepend "fixt_" to the fixture names to avoid pylint complaining about name shadowing
# https://docs.pytest.org/en/stable/reference/reference.html#pytest-fixture
@pytest.fixture(name="default_codeowners_location")
def fixt_default_codeowners_location() -> Path:
    return Path(".github/CODEOWNERS")


@pytest.fixture(name="create_temp_file_or_dir")
def fixt_create_temp_file_or_dir():
    """Fixture to create and clean up temporary files and directories."""
    created_paths: list[Path] = []

    def _create_temp_file_or_dir(location: Path, *, force_file: bool = False) -> None:
        for parent in reversed(location.parents):
            # Create and keep track of created parent directories for cleanup
            if not parent.exists():
                parent.mkdir()
                created_paths.append(parent)

        # Create the requested file or directory and keep track of it for cleanup
        # Assume that if the file path does not have an extension, it is a directory
        # The force_file flag can be used to override this behavior
        if location.suffix == "" and not force_file:
            location.mkdir()
        else:
            location.touch()
        created_paths.append(location)

    yield _create_temp_file_or_dir
    for path in reversed(created_paths):
        if path.exists():
            if path.is_dir():
                path.rmdir()
            else:
                path.unlink()


@pytest.fixture(name="create_codeowners_file")
def fixt_create_codeowners_file(create_temp_file_or_dir):
    def _create_codeowners_file(ownership_data: dict[str, list[str]], location: Path) -> None:
        create_temp_file_or_dir(location, force_file=True)
        codeowners_content = "\n".join(f"{pattern} {' '.join(owners)}" for pattern, owners in ownership_data.items())
        location.write_text(codeowners_content)

    return _create_codeowners_file


@pytest.fixture(name="create_temp_items")
def fixt_create_temp_items(create_temp_file_or_dir):
    def _create_temp_items(files: Iterable[str], temp_dir: Path) -> None:
        for file_str in files:
            # Always use forward slashes for paths, as that's what pathlib expects
            file_path = temp_dir / file_str.replace(sep, "/")
            create_temp_file_or_dir(file_path)

    return _create_temp_items
