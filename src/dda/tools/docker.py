# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property

from dda.tools.base import Tool


class Docker(Tool):
    def format_command(self, command: list[str]) -> list[str]:
        return [self.path, *command]

    @cached_property
    def path(self) -> str:
        import shutil

        return shutil.which("docker") or shutil.which("podman") or "docker"
