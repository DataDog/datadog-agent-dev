# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from os import sep
from typing import TYPE_CHECKING

import pytest

from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Iterable


@pytest.fixture(scope="module")
def default_codeowners_location() -> Path:
    return Path(".github/CODEOWNERS")


def _create_codeowners_file(ownership_data: dict[str, list[str]], location: Path) -> None:
    location.parent.ensure_dir()
    location.touch(exist_ok=True)
    codeowners_content = "\n".join(f"{pattern} {' '.join(owners)}" for pattern, owners in ownership_data.items())
    location.write_text(codeowners_content)


def _create_temp_items(files: Iterable[str], temp_dir: Path) -> None:
    for file_str in files:
        # Always use forward slashes for paths, as that's what pathlib expects
        file_path = temp_dir / file_str.replace(sep, "/")
        file_path.parent.ensure_dir()

        # Assume that if the file path does not have an extension, it is a directory
        if file_path.suffix == "":
            file_path.mkdir()
        else:
            file_path.touch()


def _test_owner_template(  # type: ignore[no-untyped-def]
    dda,
    temp_dir: Path,
    ownership_data: dict[str, list[str]],
    expected_result: dict[str, list[str]],
    codeowners_location: Path,
    extra_command_parts: Iterable[str] = (),
) -> None:
    files = expected_result.keys()
    _create_codeowners_file(ownership_data, temp_dir / codeowners_location)
    _create_temp_items(files, temp_dir)

    with temp_dir.as_cwd():
        result = dda(
            "info",
            "owners",
            "code",
            "--json",
            *extra_command_parts,
            *expected_result.keys(),
        )
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout) == expected_result


def test_single_owner(dda, temp_dir, default_codeowners_location):
    ownership_data = {
        "testfile.txt": ["@owner1"],
    }
    expected_result = ownership_data
    _test_owner_template(
        dda,
        temp_dir=temp_dir,
        ownership_data=ownership_data,
        expected_result=expected_result,
        codeowners_location=default_codeowners_location,
    )


def test_multiple_owners(dda, temp_dir, default_codeowners_location):
    ownership_data = {
        "testfile.txt": ["@owner1", "@owner2"],
    }
    expected_result = ownership_data
    _test_owner_template(
        dda,
        temp_dir=temp_dir,
        ownership_data=ownership_data,
        expected_result=expected_result,
        codeowners_location=default_codeowners_location,
    )


def test_wildcard_ownership(dda, temp_dir, default_codeowners_location):
    ownership_data = {
        "*.txt": ["@owner1"],
        "testfile.txt": ["@owner2"],
    }
    expected_result = {
        "testfile.txt": ["@owner2"],
        "otherfile.txt": ["@owner1"],
    }
    _test_owner_template(
        dda,
        temp_dir=temp_dir,
        ownership_data=ownership_data,
        expected_result=expected_result,
        codeowners_location=default_codeowners_location,
    )


def test_directory_ownership(dda, temp_dir, default_codeowners_location):
    ownership_data = {
        "subdir1": ["@owner1"],
        "subdir2": ["@owner2"],
        "subdir2/testfile2.txt": ["@owner3"],
    }
    expected_result = {
        "subdir1": ["@owner1"],
        "subdir1/testfile1.txt": ["@owner1"],
        "subdir2": ["@owner2"],
        "subdir2/testfile2.txt": ["@owner3"],
    }
    _test_owner_template(
        dda,
        temp_dir=temp_dir,
        ownership_data=ownership_data,
        expected_result=expected_result,
        codeowners_location=default_codeowners_location,
    )


def test_ownership_location(dda, temp_dir):
    ownership_data = {
        "testfile.txt": ["@owner1"],
    }
    expected_result = ownership_data
    _test_owner_template(
        dda,
        temp_dir=temp_dir,
        extra_command_parts=["--owners", "custom/CODEOWNERS"],
        codeowners_location=Path("custom/CODEOWNERS"),
        ownership_data=ownership_data,
        expected_result=expected_result,
    )


def test_complicated_situation(dda, temp_dir, default_codeowners_location):
    ownership_data = {
        "*": ["@DataDog/team-everything"],
        "*.md": ["@DataDog/team-devops", "@DataDog/team-doc"],
        ".gitlab": ["@DataDog/team-devops"],
        ".gitlab/security.yml": ["@DataDog/team-security"],
    }
    expected_result = {
        "test.txt": ["@DataDog/team-everything"],
        "README.md": [
            "@DataDog/team-devops",
            "@DataDog/team-doc",
        ],
        ".gitlab": ["@DataDog/team-devops"],
        ".gitlab/security.yml": ["@DataDog/team-security"],
        ".gitlab/ci.yml": ["@DataDog/team-devops"],
    }
    _test_owner_template(
        dda,
        temp_dir=temp_dir,
        ownership_data=ownership_data,
        expected_result=expected_result,
        codeowners_location=default_codeowners_location,
    )


def test_human_output(dda, temp_dir, helpers, default_codeowners_location):
    ownership_data = {
        "testfile.txt": ["@owner1"],
        "subdir/testfile2.txt": ["@owner2"],
        "subdir/anotherfile.txt": ["@owner1", "@owner3"],
    }

    _create_codeowners_file(ownership_data, temp_dir / default_codeowners_location)
    _create_temp_items(ownership_data.keys(), temp_dir)
    with temp_dir.as_cwd():
        result = dda("info", "owners", "code", *ownership_data.keys())
    assert result.exit_code == 0, result.stdout
    assert result.stdout == helpers.dedent(
        """
        ┌────────────────────────┬──────────────────┐
        │ testfile.txt           │ @owner1          │
        │ subdir/testfile2.txt   │ @owner2          │
        │ subdir/anotherfile.txt │ @owner1, @owner3 │
        └────────────────────────┴──────────────────┘
        """
    )
