# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.conftest import CliRunner


@pytest.fixture(name="use_temp_fixture_folder")
def fixt_use_temp_folder(temp_dir: Path) -> Callable[[str], Path]:
    def _use_temp_folder(folder_name: str) -> Path:
        shutil.copytree(Path(__file__).parent / "fixtures" / "ai_rules" / folder_name, temp_dir / folder_name)
        return Path(temp_dir) / folder_name

    return _use_temp_folder


def test_validate_rule_files_no_target_file(
    dda: CliRunner,
    use_temp_fixture_folder: Callable[[str], Path],
) -> None:
    """Test validation with multiple rule files."""

    path = use_temp_fixture_folder("simple_rules_no_target")
    with path.as_cwd():
        result = dda("validate", "ai-rules")

    result.check_exit_code(exit_code=1)


def test_validate_with_fix_flag(
    dda: CliRunner,
    use_temp_fixture_folder: Callable[[str], Path],
) -> None:
    """Test validation with fix flag when files are out of sync."""
    path = use_temp_fixture_folder("simple_rules_no_target")
    with path.as_cwd():
        result = dda("validate", "ai-rules", "--fix")

    result.check_exit_code(exit_code=0)
    assert (path / "CLAUDE.md").exists()
    content = (path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "@.cursor/rules/coding-standards.mdc" in content
    assert "@.cursor/rules/security.mdc" in content
    assert "@.cursor/rules/testing.mdc" in content
    assert "imhere.txt" not in content
    assert "@.cursor/rules/personal/my-rule.mdc" not in content
    assert "@.cursor/rules/nested/my-nested-rule.mdc" in content
    assert "@CLAUDE_PERSONAL.md" in content


def test_validate_no_cursor_rules_directory(
    dda: CliRunner,
    use_temp_fixture_folder: Callable[[str], Path],
) -> None:
    """Test validation when cursor rules directory doesn't exist."""
    path = use_temp_fixture_folder("no_cursor_rules")
    with path.as_cwd():
        result = dda("validate", "ai-rules")

    result.check_exit_code(exit_code=0)
    # Should not create target file if no rules directory
    target_file = path / "CLAUDE.md"
    assert not target_file.exists()


def test_validate_in_sync(
    dda: CliRunner,
    use_temp_fixture_folder: Callable[[str], Path],
) -> None:
    """Test validation when files are already in sync."""
    path = use_temp_fixture_folder("simple_rules_no_target")

    with path.as_cwd():
        # First fix the files
        result = dda("validate", "ai-rules", "--fix")
        result.check_exit_code(exit_code=0)

        # Then validate without fix
        result = dda("validate", "ai-rules")
        result.check_exit_code(exit_code=0)


def test_validate_out_of_sync(
    dda: CliRunner,
    use_temp_fixture_folder: Callable[[str], Path],
) -> None:
    """Test validation when files are out of sync."""
    path = use_temp_fixture_folder("out_of_sync")

    with path.as_cwd():
        result = dda("validate", "ai-rules")
        result.check_exit_code(exit_code=1)
