# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from deva._version import __version__


class TestVersionMismatch:
    def test_root(self, deva, helpers, temp_dir):
        version_file = temp_dir / ".deva-version"
        with temp_dir.as_cwd():
            version_file.write_text("0.0.0")

            result = deva("config")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            f"""
            deva version mismatch: {__version__} != 0.0.0
            """
        )

    def test_directory(self, deva, helpers, temp_dir):
        version_file = temp_dir / ".deva" / "version"
        version_file.parent.ensure_dir()
        with temp_dir.as_cwd():
            version_file.write_text("0.0.0")

            result = deva("config")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            f"""
            deva version mismatch: {__version__} != 0.0.0
            """
        )
