# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys

if sys.platform == "win32":
    PLATFORM_ID = "windows"
    PLATFORM_NAME = "Windows"
    DEFAULT_SHELL = os.environ.get("SHELL", os.environ.get("COMSPEC", "cmd"))

    def join_command_args(args: list[str]) -> str:
        import subprocess

        return subprocess.list2cmdline(args)

elif sys.platform == "darwin":
    PLATFORM_ID = "macos"
    PLATFORM_NAME = "macOS"
    DEFAULT_SHELL = os.environ.get("SHELL", "zsh")

    def join_command_args(args: list[str]) -> str:
        import shlex

        return shlex.join(args)

else:
    PLATFORM_ID = "linux"
    PLATFORM_NAME = "Linux"
    DEFAULT_SHELL = os.environ.get("SHELL", "bash")

    def join_command_args(args: list[str]) -> str:
        import shlex

        return shlex.join(args)
