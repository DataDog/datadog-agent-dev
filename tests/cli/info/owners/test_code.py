# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from dda.utils.fs import Path

if TYPE_CHECKING:
    from types import ModuleType

    from tests.conftest import CliRunner

TESTCASE_RESULTS = [
    {
        "testfile.txt": ["@owner1"],
    },
    {
        "testfile.txt": ["@owner1", "@owner2"],
    },
    {
        "testfile.txt": ["@owner2"],
        "otherfile.txt": ["@owner1"],
    },
    {
        "subdir1/": ["@owner1"],
        "subdir1/testfile1.txt": ["@owner1"],
        "subdir2/": ["@owner2"],
        "subdir2/testfile2.txt": ["@owner3"],
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
]


@pytest.fixture(scope="module", autouse=True)
def install_deps_once(dda):
    dda("self", "dep", "sync", "-f", "codeowners")
    with (
        patch("dda.cli.base.ensure_features_installed", return_value=None),
        patch("dda.tools.git.Git.get_repo_root", side_effect=lambda _path=None: Path.cwd()),
    ):
        yield


@pytest.mark.parametrize(
    ("case_number", "expected_result"),
    enumerate(TESTCASE_RESULTS),
)
def test_ownership_parsing(  # type: ignore[no-untyped-def]
    dda: CliRunner,
    case_number: int,
    expected_result: dict[str, list[str]],
) -> None:
    with (Path(__file__).parent / "fixtures" / f"test{case_number}").as_cwd():
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
    )


def test_ambiguous_directory_paths(
    dda: CliRunner,
) -> None:
    paths_to_test = [
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
    ]

    # Note that the paths referring to directories have a trailing slash
    # And that this does not depend on whether they were _passed_ with a trailing slash or not.
    expected_result = {
        "dir_with_slash/": ["@owner1"],
        "dir_without_slash/": ["@owner3"],
        "dir_with_slash/testfile.txt": ["@owner2"],
        "dir_without_slash/testfile.txt": ["@owner4"],
        "dir_with_slash/subdir_with_slash/": ["@owner5"],
        "dir_with_slash/subdir_with_slash/testfile.txt": ["@owner6"],
        "dir_with_slash/subdir_without_slash/": ["@owner7"],
        "dir_with_slash/subdir_without_slash/testfile.txt": ["@owner8"],
    }

    with (Path(__file__).parent / "fixtures" / "test_ambiguous_dirs").as_cwd():
        result = dda(
            "info",
            "owners",
            "code",
            "--json",
            *paths_to_test,
        )

    result.check(
        exit_code=0,
        stdout_json=expected_result,
    )


def test_ownership_location(
    dda: CliRunner,
) -> None:
    testcase_result = TESTCASE_RESULTS[4]
    with (Path(__file__).parent / "fixtures" / "test4").as_cwd():
        result = dda(
            "info",
            "owners",
            "code",
            "--json",
            "--owners",
            "../custom_CODEOWNERS",
            *testcase_result.keys(),
        )

    result.check(
        exit_code=0,
        stdout_json=testcase_result,
    )


def test_human_output(
    dda: CliRunner,
    helpers: ModuleType,
) -> None:
    testcase_result = TESTCASE_RESULTS[4]

    with (Path(__file__).parent / "fixtures" / "test4").as_cwd():
        result = dda("info", "owners", "code", *testcase_result.keys())

    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            """
            ┌──────────────────────┬─────────────────────────────────────────┐
            │ test.txt             │ @DataDog/team-everything                │
            │ README.md            │ @DataDog/team-devops, @DataDog/team-doc │
            │ .gitlab/             │ @DataDog/team-devops                    │
            │ .gitlab/security.yml │ @DataDog/team-security                  │
            │ .gitlab/ci.yml       │ @DataDog/team-devops                    │
            └──────────────────────┴─────────────────────────────────────────┘
            """
        ),
    )


# --- Subdirectory path resolution tests ---
# These tests verify the behavior matrix from the plan:
# paths are given relative to CWD and resolved to repo-root-relative paths.

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _resolved_fixture(name: str) -> Path:
    return Path((FIXTURES_DIR / name).resolve())


def test_file_from_subdirectory(
    dda: CliRunner,
) -> None:
    """CWD-relative file path from subdirectory is resolved to repo-root-relative."""
    fixture_root = _resolved_fixture("test3")
    with (fixture_root / "subdir1").as_cwd(), patch("dda.tools.git.Git.get_repo_root", return_value=fixture_root):
        result = dda("info", "owners", "code", "--json", "testfile1.txt")

    result.check(
        exit_code=0,
        stdout_json={"subdir1/testfile1.txt": ["@owner1"]},
    )


def test_directory_from_subdirectory(
    dda: CliRunner,
) -> None:
    """Current directory '.' from subdirectory resolves to repo-root-relative dir with trailing slash."""
    fixture_root = _resolved_fixture("test3")
    with (fixture_root / "subdir1").as_cwd(), patch("dda.tools.git.Git.get_repo_root", return_value=fixture_root):
        result = dda("info", "owners", "code", "--json", ".")

    result.check(
        exit_code=0,
        stdout_json={"subdir1/": ["@owner1"]},
    )


def test_parent_traversal_from_subdirectory(
    dda: CliRunner,
) -> None:
    """Paths with '..' from subdirectory are resolved correctly."""
    fixture_root = _resolved_fixture("test3")
    with (fixture_root / "subdir1").as_cwd(), patch("dda.tools.git.Git.get_repo_root", return_value=fixture_root):
        result = dda("info", "owners", "code", "--json", "../subdir2/testfile2.txt")

    result.check(
        exit_code=0,
        stdout_json={"subdir2/testfile2.txt": ["@owner3"]},
    )


def test_nonexistent_path_from_subdirectory(
    dda: CliRunner,
) -> None:
    """Non-existent paths produce an error."""
    fixture_root = _resolved_fixture("test3")
    with (fixture_root / "subdir1").as_cwd(), patch("dda.tools.git.Git.get_repo_root", return_value=fixture_root):
        result = dda("info", "owners", "code", "--json", "nonexistent.go", catch_exceptions=True)

    result.check_exit_code(1)


def test_explicit_codeowners_from_subdirectory(
    dda: CliRunner,
) -> None:
    """Explicit --owners path is resolved from CWD, not from repo root."""
    fixture_root = _resolved_fixture("test3")
    with (fixture_root / "subdir1").as_cwd(), patch("dda.tools.git.Git.get_repo_root", return_value=fixture_root):
        # custom_CODEOWNERS is at fixtures/custom_CODEOWNERS, two levels up from subdir1
        result = dda("info", "owners", "code", "--json", "--owners", "../../custom_CODEOWNERS", "testfile1.txt")

    # custom_CODEOWNERS has "* @DataDog/team-everything", which matches subdir1/testfile1.txt
    result.check(
        exit_code=0,
        stdout_json={"subdir1/testfile1.txt": ["@DataDog/team-everything"]},
    )


def test_multiple_paths_from_subdirectory(
    dda: CliRunner,
) -> None:
    """Multiple paths from a subdirectory are all resolved correctly."""
    fixture_root = _resolved_fixture("test3")
    with (fixture_root / "subdir1").as_cwd(), patch("dda.tools.git.Git.get_repo_root", return_value=fixture_root):
        result = dda(
            "info",
            "owners",
            "code",
            "--json",
            "testfile1.txt",
            "../subdir2/testfile2.txt",
            "../subdir2",
        )

    result.check(
        exit_code=0,
        stdout_json={
            "subdir1/testfile1.txt": ["@owner1"],
            "subdir2/testfile2.txt": ["@owner3"],
            "subdir2/": ["@owner2"],
        },
    )
