# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import ExecutionContext, Tool

if TYPE_CHECKING:
    from collections.abc import Generator

    from dda.utils.fs import Path
    from dda.utils.venv import VirtualEnv


class UV(Tool):
    """
    This will use the UV executable that comes with `dda`.

    Example usage:

    ```python
    app.tools.uv.run(["pip", "tree"])
    ```
    """

    @contextmanager
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        yield ExecutionContext(command=[self.path or "uv", *command], env_vars={})

    @cached_property
    def path(self) -> str | None:
        import shutil
        import sysconfig

        scripts_dir = sysconfig.get_path("scripts")
        old_path = os.environ.get("PATH", os.defpath)
        new_path = f"{scripts_dir}{os.pathsep}{old_path}"
        return shutil.which("uv", path=new_path)

    def virtual_env(self, path: Path) -> VirtualEnv:
        from filelock import FileLock

        from dda.utils.venv import VirtualEnv

        # `uv venv` errors if the target already exists, so concurrent creation must be serialized.
        # No lock is needed afterward: `uv` locks the environment itself during install/sync.
        path.parent.ensure_dir()
        with FileLock(f"{path}.lock"):
            if not path.is_dir():
                self.wait(
                    ["venv", str(path), "--seed", "--python", sys.executable], message="Creating virtual environment"
                )

        return VirtualEnv(path)
