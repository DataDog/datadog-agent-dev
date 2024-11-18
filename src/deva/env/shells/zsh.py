# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from deva.env.shells.interface import Shell

if TYPE_CHECKING:
    from deva.utils.fs import Path


class ZshShell(Shell):
    def get_login_command(self, *, cwd: str) -> str:
        return f"cd {self.join_args_unescaped([cwd])} && zsh -l -i"

    def format_command(self, args: list[str], *, cwd: str) -> str:
        return f"cd {self.join_args_unescaped([cwd])} && {self.join_args_unescaped(args)}"

    def collect_shared_files(self) -> list[Path]:
        shared_files = super().collect_shared_files()

        zsh_history_file = self.shared_dir / "zsh" / ".zsh_history"
        shared_files.append(zsh_history_file)

        zsh_history_file.parent.ensure_dir()
        zsh_history_file.touch()

        return shared_files
