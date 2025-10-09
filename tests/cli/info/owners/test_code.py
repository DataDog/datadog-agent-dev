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
    with patch("dda.cli.base.ensure_features_installed", return_value=None):
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
