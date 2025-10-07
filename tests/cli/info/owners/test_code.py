# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from types import ModuleType

    from tests.conftest import CliRunner


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
                "subdir1/": ["@owner1"],
                "subdir1/testfile1.txt": ["@owner1"],
                "subdir2/": ["@owner2"],
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
                ".gitlab/": ["@DataDog/team-devops"],
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


def test_ambiguous_directory_paths(
    dda: CliRunner,
    temp_dir: Path,
    create_codeowners_file: Callable[[dict[str, list[str]], Path], None],
    create_temp_items: Callable[[Iterable[str], Path], None],
    default_codeowners_location: Path,
    helpers: ModuleType,
) -> None:
    ownership_data = {
        "dir_with_slash/": ["@owner1"],
        "dir_with_slash/testfile.txt": ["@owner2"],
        "dir_without_slash": ["@owner3"],
        "dir_without_slash/testfile.txt": ["@owner4"],
        "dir_with_slash/subdir_with_slash/": ["@owner5"],
        "dir_with_slash/subdir_with_slash/testfile.txt": ["@owner6"],
        "dir_with_slash/subdir_without_slash": ["@owner7"],
        "dir_with_slash/subdir_without_slash/testfile.txt": ["@owner8"],
    }
    create_codeowners_file(ownership_data, temp_dir / default_codeowners_location)
    create_temp_items(
        (
            "dir_with_slash/testfile.txt",
            "dir_without_slash/testfile.txt",
            "dir_with_slash/subdir_with_slash/testfile.txt",
            "dir_with_slash/subdir_without_slash/testfile.txt",
        ),
        temp_dir,
    )
    with temp_dir.as_cwd():
        result = dda(
            "info",
            "owners",
            "code",
            "--json",
            "dir_with_slash",
            "dir_without_slash",
            "dir_with_slash/",
            "dir_without_slash/",
            "dir_with_slash/testfile.txt",
            "dir_without_slash/testfile.txt",
            "dir_with_slash/subdir_with_slash/",
            "dir_with_slash/subdir_without_slash/",
            "dir_with_slash/subdir_with_slash",
            "dir_with_slash/subdir_without_slash",
            "dir_with_slash/subdir_with_slash/testfile.txt",
            "dir_with_slash/subdir_without_slash/testfile.txt",
        )
    result.check(
        exit_code=0,
        stdout_json={
            "dir_with_slash/": ["@owner1"],
            "dir_without_slash/": ["@owner3"],
            "dir_with_slash/testfile.txt": ["@owner2"],
            "dir_without_slash/testfile.txt": ["@owner4"],
            "dir_with_slash/subdir_with_slash/": ["@owner5"],
            "dir_with_slash/subdir_with_slash/testfile.txt": ["@owner6"],
            "dir_with_slash/subdir_without_slash/": ["@owner7"],
            "dir_with_slash/subdir_without_slash/testfile.txt": ["@owner8"],
        },
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
