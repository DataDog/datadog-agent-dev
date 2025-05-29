# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property

from dda.tools.base import Tool
from dda.utils.fs import Path


class Go(Tool):
    """
    This will automatically set the [`GOTOOLCHAIN`](https://go.dev/doc/toolchain) environment variable to the proper
    version based on files in the current directory. The following files are considered, in order of precedence:

    - `.go-version`
    - `go.mod`
    - `go.work`

    Example usage:

    ```python
    app.tools.go.run(["build", "."])
    ```
    """

    def format_command(self, command: list[str]) -> list[str]:
        return [self.path, *command]

    def env_vars(self) -> dict[str, str]:
        return {"GOTOOLCHAIN": f"go{self.version}"} if self.version else {}

    @cached_property
    def path(self) -> str:
        import shutil

        return shutil.which("go") or "go"

    @cached_property
    def version(self) -> str | None:
        version_file = Path.cwd() / ".go-version"
        if version_file.is_file():
            return version_file.read_text().strip()

        import re

        version_pattern = re.compile(r"^go (.+)", re.MULTILINE)

        mod_file = Path.cwd() / "go.mod"
        if mod_file.is_file() and (match := version_pattern.search(mod_file.read_text())):
            return match.group(1)

        work_file = Path.cwd() / "go.work"
        if work_file.is_file() and (match := version_pattern.search(work_file.read_text())):
            return match.group(1)

        return None
