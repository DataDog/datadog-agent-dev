# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda._version import __version__


@pytest.fixture(scope="module")
def next_major_version():
    version_parts = list(map(int, __version__.split(".")[:3]))
    version_parts[0] += 1
    return ".".join(map(str, version_parts))


class TestVersionMismatch:
    def test_root(self, dda, helpers, temp_dir, next_major_version):
        version_file = temp_dir / ".dda-version"
        with temp_dir.as_cwd():
            version_file.write_text(next_major_version)
            result = dda("config")

        result.check(
            exit_code=1,
            output=helpers.dedent(
                f"""
                Repo requires at least dda version {next_major_version} but {__version__} is installed.
                Run the following command:
                dda self update
                """
            ),
        )

    def test_directory(self, dda, helpers, temp_dir, next_major_version):
        version_file = temp_dir / ".dda" / "version"
        version_file.parent.ensure_dir()
        with temp_dir.as_cwd():
            version_file.write_text(next_major_version)

            result = dda("config")

        result.check(
            exit_code=1,
            output=helpers.dedent(
                f"""
                Repo requires at least dda version {next_major_version} but {__version__} is installed.
                Run the following command:
                dda self update
                """
            ),
        )
