# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod

from deva.utils.fs import Path


class Shell(ABC):
    def __init__(self, shared_dir: Path) -> None:
        self.__shared_dir = shared_dir / "shell"

    @abstractmethod
    def get_login_command(self, *, cwd: str) -> str:
        """
        Return the shell-specific command to start a login shell.
        """

    @abstractmethod
    def format_command(self, args: list[str], *, cwd: str) -> str:
        """
        Format the shell-specific command for running a command with arguments.
        """

    def collect_shared_files(self) -> list[Path]:
        """
        Set up and return the shared shell-specific files.
        """
        shared_files: list[Path] = []

        starship_config_file = Path.home() / ".config" / "starship.toml"
        if starship_config_file.exists():
            import shutil

            shared_starship_config_file = self.shared_dir / "starship.toml"
            shared_files.append(shared_starship_config_file)

            self.shared_dir.ensure_dir()
            shutil.copy(starship_config_file, shared_starship_config_file)

        return shared_files

    @property
    def shared_dir(self) -> Path:
        return self.__shared_dir

    @staticmethod
    def join_args_unescaped(args: list[str]) -> str:
        return " ".join(f'"{arg}"' if " " in arg else arg for arg in args)
