# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Generic, NoReturn, cast

import msgspec

if TYPE_CHECKING:
    from dda.utils.editors.interface import EditorInterface


class DeveloperEnvironmentConfig(msgspec.Struct, kw_only=True):
    repos: Annotated[
        list[str],
        msgspec.Meta(
            extra={
                "params": ["-r", "--repo"],
                "help": (
                    """\
The Datadog repositories to work on, optionally with a particular branch or tag. This option may be
supplied multiple times. Examples:

- `datadog-agent` (default)
- `datadog-agent@user/test`
- `integrations-core@X.Y.Z`
"""
                ),
            }
        ),
    ] = msgspec.field(default_factory=lambda: ["datadog-agent"])
    clone: Annotated[
        bool,
        msgspec.Meta(
            extra={
                "help": "Clone the repositories remotely rather than using local checkouts",
            }
        ),
    ] = False


if TYPE_CHECKING:
    from typing_extensions import TypeVar

    from dda.cli.application import Application
    from dda.config.model.storage import StorageDirs
    from dda.env.models import EnvironmentStatus
    from dda.utils.fs import Path

    ConfigT = TypeVar("ConfigT", bound=DeveloperEnvironmentConfig, default=DeveloperEnvironmentConfig)
else:
    from typing import TypeVar

    ConfigT = TypeVar("ConfigT")


class DeveloperEnvironmentInterface(ABC, Generic[ConfigT]):
    """
    This interface defines the behavior of a developer environment.
    """

    def __init__(
        self,
        *,
        app: Application,
        name: str,
        instance: str,
        config: ConfigT | None = None,
    ) -> None:
        self.__app = app
        self.__name = name
        self.__instance = instance
        self.__config = config

    @abstractmethod
    def start(self) -> None:
        """
        This method starts the developer environment. If this method returns early, the environment's
        [status][dda.env.dev.interface.DeveloperEnvironmentInterface.status] should contain
        information about the startup progress.

        This method will only be called if the environment's
        [status][dda.env.dev.interface.DeveloperEnvironmentInterface.status] is
        [stopped][dda.env.models.EnvironmentState.STOPPED] or
        [nonexistent][dda.env.models.EnvironmentState.NONEXISTENT].

        Users trigger this method by running the [`env dev start`](../../../cli/commands.md#dda-env-dev-start) command.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        This method stops the developer environment. If this method returns early, the
        environment's [status][dda.env.dev.interface.DeveloperEnvironmentInterface.status]
        should contain information about the shutdown progress.

        This method will only be called if the environment's
        [status][dda.env.dev.interface.DeveloperEnvironmentInterface.status] is
        [started][dda.env.models.EnvironmentState.STARTED].

        Users trigger this method by running the [`env dev stop`](../../../cli/commands.md#dda-env-dev-stop) command.
        """

    @abstractmethod
    def remove(self) -> None:
        """
        This method removes the developer environment and all associated state.

        This method will only be called if the environment's
        [status][dda.env.dev.interface.DeveloperEnvironmentInterface.status] is
        [stopped][dda.env.models.EnvironmentState.STOPPED] or in an
        [error][dda.env.models.EnvironmentState.ERROR] state.

        Users trigger this method by running the [`env dev remove`](../../../cli/commands.md#dda-env-dev-remove)
        command or with the `-r`/`--remove` flag of the [`env dev stop`](../../../cli/commands.md#dda-env-dev-stop)
        command.
        """

    @abstractmethod
    def status(self) -> EnvironmentStatus:
        """
        This method returns the current status of the developer environment.
        """

    @abstractmethod
    def code(self, *, editor: EditorInterface, repo: str | None = None) -> None:
        """
        This method opens the developer environment's code in the configured editor.

        Users trigger this method by running the [`env dev code`](../../../cli/commands.md#dda-env-dev-code) command.

        Parameters:
            editor: The editor to use.
            repo: The repository to open the code for, or `None` to open the code for the first
                [configured repository][dda.env.dev.interface.DeveloperEnvironmentConfig.repos].
        """

    @abstractmethod
    def run_command(self, command: list[str], *, repo: str | None = None) -> None:
        """
        This method runs a command inside the developer environment.

        Users trigger this method by running the [`env dev run`](../../../cli/commands.md#dda-env-dev-run) command.

        Parameters:
            command: The command to run inside the developer environment.
            repo: The repository to run the command for, or `None` to run the command for the first
                [configured repository][dda.env.dev.interface.DeveloperEnvironmentConfig.repos].
        """

    @abstractmethod
    def launch_shell(self, *, repo: str | None = None) -> NoReturn:
        """
        This method starts an interactive shell inside the developer environment.

        Users trigger this method by running the [`env dev shell`](../../../cli/commands.md#dda-env-dev-shell) command.

        Parameters:
            repo: The repository to run the shell for, or `None` to run the shell for the first
                [configured repository][dda.env.dev.interface.DeveloperEnvironmentConfig.repos].
        """

    @abstractmethod
    def export_files(
        self,
        sources: tuple[str, ...],  # Passed as string since they are inside the env filesystem
        destination: Path,
        recursive: bool,  # noqa: FBT001
        force: bool,  # noqa: FBT001
        mkpath: bool,  # noqa: FBT001
    ) -> None:
        """
        This method exports files from the developer environment to the host filesystem.

        Parameters:
            sources: The paths to files/directories in the developer environment to export.
            destination: The destination directory on the host filesystem.
            recursive: Whether to export files and directories recursively. If False, all sources must be files.
            force: Whether to overwrite existing files. Without this option, an error will be raised if the destination file/directory already exists.
            mkpath: Whether to create the destination directories and their parents if they do not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def import_files(
        self,
        sources: tuple[Path, ...],
        destination: str,  # Passed as string since it is inside the env filesystem
        recursive: bool,  # noqa: FBT001
        force: bool,  # noqa: FBT001
        mkpath: bool,  # noqa: FBT001
    ) -> None:
        """
        This method imports files from the host filesystem into the developer environment.

        Parameters:
            sources: The paths to files/directories in the developer environment to export.
            destination: The destination directory on the host filesystem.
            recursive: Whether to export files and directories recursively. If False, all sources must be files.
            force: Whether to overwrite existing files. Without this option, an error will be raised if the destination file/directory already exists.
            mkpath: Whether to create the destination directories and their parents if they do not exist.
        """
        raise NotImplementedError

    def launch_gui(self) -> NoReturn:
        """
        This method starts an interactive GUI inside the developer environment using e.g. RDP or VNC.
        """
        raise NotImplementedError

    def remove_cache(self) -> None:
        """
        This method removes the developer environment's cache that is persisted between lifecycles.
        """
        raise NotImplementedError

    def cache_size(self) -> int:
        """
        This method returns the size of the developer environment's cache in bytes.
        """
        raise NotImplementedError

    @property
    def app(self) -> Application:
        """
        The [`Application`][dda.cli.application.Application] instance.
        """
        return self.__app

    @property
    def name(self) -> str:
        """
        The name of the environment type e.g. `linux-container`.
        """
        return self.__name

    @property
    def instance(self) -> str:
        """
        The instance of the environment e.g. `default`.
        """
        return self.__instance

    @cached_property
    def storage_dirs(self) -> StorageDirs:
        """
        The storage directories for the environment.
        """
        return self.app.config.storage.join("env", "dev", self.name, self.instance)

    @cached_property
    def config(self) -> ConfigT:
        """
        The user-defined configuration as an instance of the
        [`DeveloperEnvironmentConfig`][dda.env.dev.interface.DeveloperEnvironmentConfig] class, or subclass thereof.
        """
        return self.__load_config() if self.__config is None else self.__config

    @classmethod
    def config_class(cls) -> type[DeveloperEnvironmentConfig]:
        """
        The [`DeveloperEnvironmentConfig`][dda.env.dev.interface.DeveloperEnvironmentConfig] class, or subclass thereof,
        that is used to configure the environment.
        """
        return DeveloperEnvironmentConfig

    @cached_property
    def config_file(self) -> Path:
        """
        The path to the JSON file that is used to persist the environment's configuration until the environment
        is [removed][dda.env.dev.interface.DeveloperEnvironmentInterface.remove].
        """
        return self.storage_dirs.data.joinpath("config.json")

    @cached_property
    def shared_dir(self) -> Path:
        """
        The path to the directory that is used to share data between the host and the environment.
        """
        return self.storage_dirs.data.joinpath(".shared")

    @cached_property
    def global_shared_dir(self) -> Path:
        """
        The path to the directory that is used to share data between all environments.
        """
        return self.storage_dirs.data.parent.joinpath(".shared")

    @cached_property
    def default_repo(self) -> str:
        """
        The default repository to work on.
        """
        return self.config.repos[0].split("@")[0]

    def save_config(self) -> None:
        self.config_file.parent.ensure_dir()
        self.config_file.write_bytes(msgspec.json.encode(self.config))

    def remove_config(self) -> None:
        if self.config_file.is_file():
            self.config_file.unlink()

    def __load_config(self) -> ConfigT:
        config = (
            msgspec.json.decode(self.config_file.read_bytes(), type=self.config_class())
            if self.config_file.is_file()
            else self.config_class()()
        )
        return cast(ConfigT, config)
