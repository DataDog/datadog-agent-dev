# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from os import sep
from typing import TYPE_CHECKING

import pytest

from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from types import ModuleType

    from tests.conftest import CliRunner


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


@pytest.mark.parametrize(
    ("ownership_data", "expected_result"),
    [
        # Test case 1: Single owner for a single file
        (
            {
                "testfile.txt": ["@owner1"],
            },
            None,  # expected_result will default to ownership_data
        ),
        # Test case 2: Multiple owners for a single file
        (
            {
                "testfile.txt": ["@owner1", "@owner2"],
            },
            None,
        ),
        # Test case 3: Wildcard ownership
        (
            {
                "*.txt": ["@owner1"],
                "testfile.txt": ["@owner2"],
            },
            {
                "testfile.txt": ["@owner2"],
                "otherfile.txt": ["@owner1"],
            },
        ),
        # Test case 4: Directory ownership
        (
            {
                "subdir1": ["@owner1"],
                "subdir2": ["@owner2"],
                "subdir2/testfile2.txt": ["@owner3"],
            },
            {
                "subdir1": ["@owner1"],
                "subdir1/testfile1.txt": ["@owner1"],
                "subdir2": ["@owner2"],
                "subdir2/testfile2.txt": ["@owner3"],
            },
        ),
        # Test case 5: Complicated situation with multiple patterns
        (
            {
                "*": ["@DataDog/team-everything"],
                "*.md": ["@DataDog/team-devops", "@DataDog/team-doc"],
                ".gitlab": ["@DataDog/team-devops"],
                ".gitlab/security.yml": ["@DataDog/team-security"],
            },
            {
                "test.txt": ["@DataDog/team-everything"],
                "README.md": [
                    "@DataDog/team-devops",
                    "@DataDog/team-doc",
                ],
                ".gitlab": ["@DataDog/team-devops"],
                ".gitlab/security.yml": ["@DataDog/team-security"],
                ".gitlab/ci.yml": ["@DataDog/team-devops"],
            },
        ),
    ],
)
def test_ownership_parsing(  # type: ignore[no-untyped-def]
    dda: CliRunner,
    temp_dir: Path,
    create_codeowners_file: Callable[[dict[str, list[str]], Path], None],
    create_temp_items: Callable[[Iterable[str], Path], None],
    default_codeowners_location: Path,
    ownership_data: dict[str, list[str]],
    expected_result: dict[str, list[str]] | None,
    helpers: ModuleType,
) -> None:
    if expected_result is None:
        expected_result = ownership_data
    files = expected_result.keys()
    create_codeowners_file(ownership_data, temp_dir / default_codeowners_location)
    create_temp_items(files, temp_dir)

    with temp_dir.as_cwd():
        result = dda(
            "info",
            "owners",
            "code",
            "--json",
            *expected_result.keys(),
        )

    result.check(
        exit_code=0,
        stdout_json=expected_result,
        stderr=helpers.dedent(
            """
            Synchronizing dependencies
            """
        ),
    )


def test_ownership_location(
    dda: CliRunner,
    temp_dir: Path,
    create_codeowners_file: Callable[[dict[str, list[str]], Path], None],
    create_temp_items: Callable[[Iterable[str], Path], None],
    helpers: ModuleType,
) -> None:
    ownership_data = {
        "testfile.txt": ["@owner1"],
    }
    expected_result = ownership_data
    custom_location = Path("custom/CODEOWNERS")
    create_codeowners_file(ownership_data, temp_dir / custom_location)
    create_temp_items(ownership_data.keys(), temp_dir)
    with temp_dir.as_cwd():
        result = dda(
            "info",
            "owners",
            "code",
            "--json",
            "--owners",
            custom_location.as_posix(),
            *expected_result.keys(),
        )

    result.check(
        exit_code=0,
        stdout_json=expected_result,
        stderr=helpers.dedent(
            """
            Synchronizing dependencies
            """
        ),
    )


def test_human_output(
    dda: CliRunner,
    temp_dir: Path,
    helpers: ModuleType,
    create_codeowners_file: Callable[[dict[str, list[str]], Path], None],
    create_temp_items: Callable[[Iterable[str], Path], None],
    default_codeowners_location: Path,
) -> None:
    ownership_data = {
        "testfile.txt": ["@owner1"],
        "subdir/testfile2.txt": ["@owner2"],
        "subdir/anotherfile.txt": ["@owner1", "@owner3"],
    }

    create_codeowners_file(ownership_data, temp_dir / default_codeowners_location)
    create_temp_items(ownership_data.keys(), temp_dir)
    with temp_dir.as_cwd():
        result = dda("info", "owners", "code", *ownership_data.keys())

    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            """
            ┌────────────────────────┬──────────────────┐
            │ testfile.txt           │ @owner1          │
            │ subdir/testfile2.txt   │ @owner2          │
            │ subdir/anotherfile.txt │ @owner1, @owner3 │
            └────────────────────────┴──────────────────┘
            """
        ),
        output=helpers.dedent(
            """
            Synchronizing dependencies
            ┌────────────────────────┬──────────────────┐
            │ testfile.txt           │ @owner1          │
            │ subdir/testfile2.txt   │ @owner2          │
            │ subdir/anotherfile.txt │ @owner1, @owner3 │
            └────────────────────────┴──────────────────┘
            """
        ),
    )
