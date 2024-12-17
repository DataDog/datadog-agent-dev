# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Generic, NoReturn, cast

import msgspec


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

    from deva.cli.application import Application
    from deva.config.model.storage import StorageDirs
    from deva.env.models import EnvironmentStatus
    from deva.utils.fs import Path

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
        This method starts the developer environment. If this method returns early, the `status`
        method should contain information about the startup progress.

        This method will only be called if the environment is stopped or nonexistent.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        This method stops the developer environment. If this method returns early, the `status`
        method should contain information about the shutdown progress.

        This method will only be called if the environment is started.
        """

    @abstractmethod
    def remove(self) -> None:
        """
        This method removes the developer environment and all associated state.

        This method will only be called if the environment is stopped or in an error state.
        """

    @abstractmethod
    def status(self) -> EnvironmentStatus:
        """
        This method returns the current status of the developer environment.
        """

    @abstractmethod
    def code(self, *, repo: str | None = None) -> None:
        """
        This method opens the developer environment's code in the configured editor.
        """

    @abstractmethod
    def run_command(self, command: list[str], *, repo: str | None = None) -> None:
        """
        This method runs a command inside the developer environment.
        """

    @abstractmethod
    def launch_shell(self, *, repo: str | None = None) -> NoReturn:
        """
        This method starts an interactive shell inside the developer environment.
        """

    def launch_gui(self) -> NoReturn:
        """
        This method starts an interactive GUI inside the developer environment using e.g. RDP or VNC.
        """
        raise NotImplementedError

    @property
    def app(self) -> Application:
        return self.__app

    @property
    def name(self) -> str:
        return self.__name

    @property
    def instance(self) -> str:
        return self.__instance

    @cached_property
    def storage_dirs(self) -> StorageDirs:
        return self.app.config.storage.join("env", "dev", self.name, self.instance)

    @cached_property
    def config(self) -> ConfigT:
        return self.__load_config() if self.__config is None else self.__config

    @classmethod
    def config_class(cls) -> type[DeveloperEnvironmentConfig]:
        return DeveloperEnvironmentConfig

    @cached_property
    def config_file(self) -> Path:
        return self.storage_dirs.data.joinpath("config.json")

    @cached_property
    def shared_dir(self) -> Path:
        return self.storage_dirs.data.joinpath(".shared")

    @cached_property
    def global_shared_dir(self) -> Path:
        return self.storage_dirs.data.parent.joinpath(".shared")

    @cached_property
    def default_repo(self) -> str:
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
