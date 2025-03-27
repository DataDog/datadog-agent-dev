# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import Tool

if TYPE_CHECKING:
    from dda.utils.fs import Path
    from dda.utils.venv import VirtualEnv


class UV(Tool):
    def format_command(self, command: list[str]) -> list[str]:
        return [self.path, *command]

    @cached_property
    def path(self) -> str:
        import shutil
        import sysconfig

        scripts_dir = sysconfig.get_path("scripts")
        old_path = os.environ.get("PATH", os.defpath)
        new_path = f"{scripts_dir}{os.pathsep}{old_path}"
        return shutil.which("uv", path=new_path) or "uv"

    def virtual_env(self, path: Path) -> VirtualEnv:
        from dda.utils.venv import VirtualEnv

        if not path.is_dir():
            self.wait(["venv", str(path), "--seed", "--python", sys.executable], message="Creating virtual environment")

        return VirtualEnv(path)
