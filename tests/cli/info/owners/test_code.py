# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations
from typing import Iterable

from dda.utils.fs import Path, temp_directory

import json


def _create_codeowners_file(ownership_data: dict[str, list[str]], location: Path):
    location.parent.ensure_dir()
    location.touch(exist_ok=True)
    codeowners_content = "\n".join(
        f"{pattern} {' '.join(owners)}" for pattern, owners in ownership_data.items()
    )
    location.write_text(codeowners_content)


def _create_temp_files(files: Iterable[str], temp_dir: Path) -> None:
    for file_str in files:
        file_path = temp_dir / file_str
        file_path.parent.ensure_dir()
        file_path.touch()


def _test_owner_template(
    dda,
    ownership_data: dict[str, list[str]],
    expected_result: dict[str, list[str]],
    extra_command_parts: Iterable[str] = (),
    codeowners_location: Path = Path(".github/CODEOWNERS"),
):
    files = expected_result.keys()
    with temp_directory() as temp_dir:
        _create_codeowners_file(ownership_data, temp_dir / codeowners_location)
        _create_temp_files(files, temp_dir)

        with temp_dir.as_cwd():
            result = dda(
                "info",
                "owners",
                "code",
                "--no-pretty",
                *extra_command_parts,
                *expected_result.keys(),
            )
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout) == expected_result


def test_single_owner(dda):
    ownership_data = {
        "testfile.txt": ["@owner1"],
    }
    expected_result = ownership_data
    _test_owner_template(
        dda,
        ownership_data=ownership_data,
        expected_result=expected_result,
    )
