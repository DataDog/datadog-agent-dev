# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import Tool
from dda.utils.platform import PLATFORM_ID, which

if TYPE_CHECKING:
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

    def format_command(self, command: list[str]) -> list[str]:
        return [self.path, *command]

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
