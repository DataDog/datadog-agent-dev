# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.env.shells.interface import Shell

if TYPE_CHECKING:
    from dda.utils.fs import Path


class NuShell(Shell):
    def get_login_command(self, *, cwd: str) -> str:
        return self.__sh_command(["nu", "-l", "-i"], cwd=cwd)

    def format_command(self, args: list[str], *, cwd: str) -> str:
        import shlex

        return self.__sh_command(["nu", "-c", shlex.join(args)], cwd=cwd)

    def collect_shared_files(self) -> list[Path]:
        shared_files = super().collect_shared_files()

        nu_history_dir = self.shared_dir / "nu"
        nu_history_dir.ensure_dir()

        # https://sqlite.org/wal.html#walfile
        # https://sqlite.org/walformat.html#shm
        for history_file in ("history.sqlite3", "history.sqlite3-wal", "history.sqlite3-shm"):
            nu_history_file = nu_history_dir / history_file
            nu_history_file.touch()
            shared_files.append(nu_history_file)

        return shared_files

    def __sh_command(self, args: list[str], *, cwd: str) -> str:
        from dda.utils.platform import join_command_args

        # https://github.com/nushell/nushell/issues/10219
        return join_command_args([
            "sh",
            "-l",
            "-c",
            f"cd {self.join_args_unescaped([cwd])} && {join_command_args(args)}",
        ])
