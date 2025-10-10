# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from dda.utils.fs import Path
    from tests.conftest import CliRunner

@pytest.fixture(name="create_cursor_rules")
def fixt_create_cursor_rules(create_temp_path):
    def _create_cursor_rules(rules_data: dict[str, str], cursor_rules_dir: Path) -> None:
        """Create cursor rule files with given content."""
        for filename, content in rules_data.items():
            rule_file = cursor_rules_dir / filename
            create_temp_path(rule_file, force_file=True)
            rule_file.write_text(content, encoding="utf-8")

    return _create_cursor_rules


def test_validate_rule_files_no_target_file(
    dda: CliRunner,
    temp_dir: Path,
    create_cursor_rules: Callable[[dict[str, str], Path], None],
) -> None:
    """Test validation with multiple rule files."""
    cursor_rules_dir = temp_dir / ".cursor" / "rules"

    rules_data = {
        "coding-standards.mdc": "Use TypeScript for all frontend code.",
        "security.mdc": "Always validate input parameters.",
        "testing.mdc": "Write unit tests for all functions.",
    }

    create_cursor_rules(rules_data, cursor_rules_dir)

    with temp_dir.as_cwd():
        result = dda("validate", "ai-rules")

    assert result.exit_code == 1


def test_validate_with_fix_flag(
    dda: CliRunner,
    temp_dir: Path,
    create_cursor_rules: Callable[[dict[str, str], Path], None],
) -> None:
    """Test validation with fix flag when files are out of sync."""
    cursor_rules_dir = temp_dir / ".cursor" / "rules"
    target_file = temp_dir / "CLAUDE.md"

    rules_data = {"test-rule.mdc": "This is a test rule."}

    create_cursor_rules(rules_data, cursor_rules_dir)

    with temp_dir.as_cwd():
        result = dda("validate", "ai-rules", "--fix")

    assert result.exit_code == 0
    assert target_file.exists()

    content = target_file.read_text(encoding="utf-8")
    assert f"@{cursor_rules_dir.relative_to(target_file.parent) / 'test-rule.mdc'}" in content


def test_validate_no_cursor_rules_directory(
    dda: CliRunner,
    temp_dir: Path,
) -> None:
    """Test validation when cursor rules directory doesn't exist."""
    with temp_dir.as_cwd():
        result = dda("validate", "ai-rules")

    assert result.exit_code == 0  # Should succeed when no rules directory
    # Should not create target file if no rules directory
    target_file = temp_dir / "CLAUDE.md"
    assert not target_file.exists()


def test_validate_ignore_non_mdc_files(
    dda: CliRunner,
    temp_dir: Path,
    create_cursor_rules: Callable[[dict[str, str], Path], None],
    create_temp_path: Callable[[Path], None],
) -> None:
    """Test that validation ignores files that don't end with .mdc."""
    cursor_rules_dir = temp_dir / ".cursor" / "rules"
    target_file = temp_dir / "CLAUDE.md"

    # Create .mdc file and other files that should be ignored
    rules_data = {"valid-rule.mdc": "This is a valid rule."}
    create_cursor_rules(rules_data, cursor_rules_dir)

    # Create files that should be ignored
    ignored_file = cursor_rules_dir / "ignored.txt"
    create_temp_path(ignored_file)
    ignored_file.write_text("This should be ignored", encoding="utf-8")

    with temp_dir.as_cwd():
        result = dda("validate", "ai-rules", "--fix")

    assert result.exit_code == 0
    assert target_file.exists()

    content = target_file.read_text(encoding="utf-8")
    assert f"@{cursor_rules_dir.relative_to(target_file.parent) / 'valid-rule.mdc'}" in content
    assert "ignored.txt" not in content


def test_validate_in_sync(
    dda: CliRunner,
    temp_dir: Path,
    create_cursor_rules: Callable[[dict[str, str], Path], None],
) -> None:
    """Test validation when files are already in sync."""
    cursor_rules_dir = temp_dir / ".cursor" / "rules"

    rules_data = {"test-rule.mdc": "This is a test rule."}

    create_cursor_rules(rules_data, cursor_rules_dir)

    with temp_dir.as_cwd():
        # First fix the files
        result = dda("validate", "ai-rules", "--fix")
        assert result.exit_code == 0

        # Then validate without fix
        result = dda("validate", "ai-rules")
        assert result.exit_code == 0


def test_validate_out_of_sync(
    dda: CliRunner,
    temp_dir: Path,
    create_cursor_rules: Callable[[dict[str, str], Path], None],
    create_temp_path: Callable[[Path], None],
) -> None:
    """Test validation when files are out of sync."""
    cursor_rules_dir = temp_dir / ".cursor" / "rules"
    target_file = temp_dir / "CLAUDE.md"

    rules_data = {"test-rule.mdc": "This is a test rule."}

    create_cursor_rules(rules_data, cursor_rules_dir)

    # Create an outdated target file
    create_temp_path(target_file)
    target_file.write_text("Old content", encoding="utf-8")

    with temp_dir.as_cwd():
        result = dda("validate", "ai-rules")
        assert result.exit_code == 1




def test_validate_ignore_personal_rules(
    dda: CliRunner,
    temp_dir: Path,
    create_cursor_rules: Callable[[dict[str, str], Path], None],
) -> None:
    """Test that personal rules are ignored."""
    cursor_rules_dir = temp_dir / ".cursor" / "rules"
    target_file = temp_dir / "CLAUDE.md"

    rules_data = {"valid-rule.mdc": "This is a valid rule.", "personal/my-rule.mdc": "This should be ignored."}

    create_cursor_rules(rules_data, cursor_rules_dir)

    with temp_dir.as_cwd():
        print(os.listdir("."))
        result = dda("validate", "ai-rules", "--fix")

    assert result.exit_code == 0
    assert target_file.exists()

    content = target_file.read_text(encoding="utf-8")
    assert f"@{cursor_rules_dir.relative_to(target_file.parent) / 'valid-rule.mdc'}" in content
    assert "my-rule.mdc" not in content
