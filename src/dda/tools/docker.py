# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import ExecutionContext, Tool

if TYPE_CHECKING:
    from collections.abc import Generator


class Docker(Tool):
    """
    If `docker` is not on the PATH, this will try to use `podman` instead. Additionally, Docker CLI hints are disabled
    to have less verbosity and a more consistent experience across different Docker-compatible tools.

    Example usage:

    ```python
    app.tools.docker.run(["build", ".", "--tag", "my-image"])
    ```
    """

    @contextmanager
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        yield ExecutionContext(command=[self.path, *command], env_vars={"DOCKER_CLI_HINTS": "0"})

    @cached_property
    def path(self) -> str:
        import shutil

        return shutil.which("docker") or shutil.which("podman") or "docker"
