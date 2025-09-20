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

    This also makes modifying the installation of UV itself safe on Windows.
    """

    @contextmanager
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        if self.path is None:
            yield ExecutionContext(command=["uv", *command], env_vars={})
            return

        import shutil

        from dda.utils.fs import Path

        path = Path(self.path)
        safe_path = path.with_stem(f"{path.stem}-{path.id}")
        shutil.copy2(self.path, safe_path)

        try:
            yield ExecutionContext(command=[str(safe_path), *command], env_vars={})
        finally:
            safe_path.unlink()

    @cached_property
    def path(self) -> str | None:
        import shutil
        import sysconfig

        scripts_dir = sysconfig.get_path("scripts")
        old_path = os.environ.get("PATH", os.defpath)
        new_path = f"{scripts_dir}{os.pathsep}{old_path}"
        return shutil.which("uv", path=new_path)

    def virtual_env(self, path: Path) -> VirtualEnv:
        from dda.utils.venv import VirtualEnv

        if not path.is_dir():
            self.wait(["venv", str(path), "--seed", "--python", sys.executable], message="Creating virtual environment")

        return VirtualEnv(path)
