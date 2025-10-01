# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import ExecutionContext, Tool
from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Generator
    from os import PathLike
    from typing import Any


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

    @contextmanager
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        yield ExecutionContext(
            command=[self.path, *command],
            env_vars={"GOTOOLCHAIN": f"go{self.version}"} if self.version else {},
        )

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

    def _build(self, args: list[str], **kwargs: Any) -> str:
        """Run a raw go build command."""
        return self.capture(["build", *args], check=True, **kwargs)

    def build(
        self,
        entrypoint: str | PathLike,
        output: str | PathLike,
        *args: str,
        build_tags: set[str] | None = None,
        go_mod: str | PathLike | None = None,
        gcflags: str | None = None,
        ldflags: str | None = None,
        force_rebuild: bool = False,
        **kwargs: dict[str, Any],
    ) -> str:
        """
        Run an instrumented Go build command.

        Args:
            entrypoint: The go file / directory to build.
            output: The path to the output binary.
            *args: Extra positional arguments to pass to the go build command.
            go_mod: Path to a go.mod file to use. By default will not be specified to the build command.
            gcflags: The gcflags (go compiler flags) to use. Empty by default.
            ldflags: The ldflags (go linker flags) to use. Empty by default.
            force_rebuild: Whether to force a rebuild of the package and bypass the build cache.
            **kwargs: Additional arguments to pass to the go build command.
        """
        from platform import machine as architecture

        from dda.config.constants import Verbosity
        from dda.utils.platform import PLATFORM_ID

        command_parts = [
            "-trimpath",  # Always use trimmed paths instead of absolute file system paths # NOTE: This might not work with delve
            f"-o={output}",
        ]

        if force_rebuild:
            command_parts.append("-a")

        # Enable data race detection on platforms that support it (all execpt windows arm64)
        if not (PLATFORM_ID == "windows" and architecture() == "arm64"):
            command_parts.append("-race")

        if self.app.config.terminal.verbosity >= Verbosity.VERBOSE:
            command_parts.append("-v")
        if self.app.config.terminal.verbosity >= Verbosity.DEBUG:
            command_parts.append("-x")

        if go_mod:
            command_parts.append(f"-mod={go_mod}")
        if gcflags:
            command_parts.append(f"-gcflags={gcflags}")
        if ldflags:
            command_parts.append(f"-ldflags={ldflags}")

        if build_tags:
            command_parts.append(f"-tags={' '.join(sorted(build_tags))}")

        command_parts.extend(args)
        command_parts.append(str(entrypoint))

        return self._build(command_parts, **kwargs)
