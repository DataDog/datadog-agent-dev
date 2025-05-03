# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from functools import cached_property
from typing import TYPE_CHECKING, Any

from dda.tools.base import Tool

if TYPE_CHECKING:
    from types import TracebackType

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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__safe_path: str | None = None

    def format_command(self, command: list[str]) -> list[str]:
        return [self.__safe_path or self.path or "uv", *command]

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

    def __enter__(self) -> None:
        if self.path is not None:
            import shutil

            from dda.utils.fs import Path

            path = Path(self.path)
            safe_path = path.with_stem(f"{path.stem}-{path.id}")
            shutil.copy2(self.path, safe_path)
            self.__safe_path = str(safe_path)

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self.__safe_path is not None:
            os.remove(self.__safe_path)
            self.__safe_path = None
