# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from contextlib import contextmanager
from functools import cache, cached_property
from typing import TYPE_CHECKING, Any

from dda.tools.base import ExecutionContext, Tool
from dda.utils.platform import PLATFORM_ID, which

if TYPE_CHECKING:
    from collections.abc import Generator

    from dda.utils.fs import Path


class Bazel(Tool):
    """
    Example usage:

    ```python
    app.tools.bazel.run(["build", "//..."])
    ```

    This automatically downloads the latest release of [Bazelisk](https://github.com/bazelbuild/bazelisk)
    to an internal location if `bazel` nor `bazelisk` are already on PATH.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Avoid platform-specific command line length limits by default
        self.__ignore_arg_limits = False

    @contextmanager
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        first_arg: str | None = None
        for arg in command:
            if not arg.startswith("-"):
                first_arg = arg
                break

        if first_arg is None:
            yield ExecutionContext(command=[self.path, *command], env_vars={})
            return

        try:
            sep_index = command.index("--")
        except ValueError:
            if self.__ignore_arg_limits:
                yield ExecutionContext(command=[self.path, *command], env_vars={})
                return

            msg = "Bazel arguments must come after the `--` separator"
            raise ValueError(msg) from None

        if first_arg in self.target_accepting_commands:
            arg_file_flag = "--target_pattern_file"
        elif first_arg in self.query_accepting_commands:
            arg_file_flag = "--query_file"
        else:
            yield ExecutionContext(command=[self.path, *command], env_vars={})
            return

        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile(mode="w", encoding="utf-8") as f:
            f.write("\n".join(command[sep_index + 1 :]))
            f.flush()

            yield ExecutionContext(
                command=[self.path, *command[:sep_index], arg_file_flag, f.name],
                env_vars={},
            )

    @property
    def managed(self) -> bool:
        if self.app.config.tools.bazel.managed == "auto":
            return self.__external_path is None

        return self.app.config.tools.bazel.managed

    @cached_property
    def path(self) -> str:
        if not self.managed:
            return self.__external_path or "bazel"

        if not self.__internal_path.is_file():
            self.update()

        return str(self.__internal_path)

    def update(self) -> None:
        self.__internal_path.parent.ensure_dir()
        with self.app.status("Downloading Bazelisk"):
            self.app.http.download(get_download_url(), path=self.__internal_path)

    @cached_property
    def __internal_path(self) -> Path:
        return self.app.config.storage.cache.joinpath("tools", "bazel", "bazelisk").as_exe()

    @cached_property
    def __external_path(self) -> str | None:
        for name in ("bazel", "bazelisk"):
            path = which(name)
            if path is not None:
                return path

        return None

    @property
    def target_accepting_commands(self) -> frozenset[str]:
        return target_accepting_commands()

    @property
    def query_accepting_commands(self) -> frozenset[str]:
        return query_accepting_commands()

    @contextmanager
    def ignore_arg_limits(self) -> Generator[None, None, None]:
        self.__ignore_arg_limits = True
        try:
            yield
        finally:
            self.__ignore_arg_limits = False


def get_download_url() -> str:
    import platform

    system = "darwin" if PLATFORM_ID == "macos" else PLATFORM_ID
    arch = platform.machine().lower()
    if arch == "x86_64":
        arch = "amd64"
    elif arch == "aarch64":
        arch = "arm64"

    url = f"https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-{system}-{arch}"
    return f"{url}.exe" if PLATFORM_ID == "windows" else url


@cache
def target_accepting_commands() -> frozenset[str]:
    return frozenset({"build", "coverage", "fetch", "run", "test"})


@cache
def query_accepting_commands() -> frozenset[str]:
    return frozenset({"aquery", "cquery", "query"})
