# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, NoReturn

import msgspec

if TYPE_CHECKING:
    from deva.cli.application import Application
    from deva.config.model.storage import StorageDirs
    from deva.env.models import EnvironmentStatus
    from deva.utils.fs import Path


class DeveloperEnvironmentConfig(msgspec.Struct, kw_only=True):
    ref: Annotated[
        str,
        msgspec.Meta(
            extra={
                "help": "The Git reference for the `datadog-agent` repository",
            }
        ),
    ] = "main"


class DeveloperEnvironmentInterface(ABC):
    """
    This interface defines the behavior of a developer environment.
    """

    def __init__(
        self,
        *,
        app: Application,
        name: str,
        config: DeveloperEnvironmentConfig | None = None,
    ) -> None:
        self.__app = app
        self.__name = name
        self.__config = config

    @abstractmethod
    def start(self) -> None:
        """
        This method starts the developer environment. If this method returns early, the `status`
        method should contain information about the startup progress.

        This method will never be called if the environment is already running.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        This method stops the developer environment. If this method returns early, the `status`
        method should contain information about the shutdown progress.
        """

    @abstractmethod
    def remove(self) -> None:
        """
        This method removes the developer environment and all associated state. This will never be
        called if the `status` method indicates that the environment is not `inactive`.
        """

    @abstractmethod
    def status(self) -> EnvironmentStatus:
        """
        This method returns the current status of the developer environment.
        """

    @abstractmethod
    def shell(self) -> NoReturn:
        """
        This method starts an interactive shell inside the developer environment.
        """

    @abstractmethod
    def run_command(self, command: list[str]) -> None:
        """
        This method runs a command inside the developer environment.
        """

    @property
    def app(self) -> Application:
        return self.__app

    @property
    def name(self) -> str:
        return self.__name

    @cached_property
    def storage_dirs(self) -> StorageDirs:
        return self.app.config.storage.join("env", "dev", self.__name)

    @cached_property
    def config(self) -> DeveloperEnvironmentConfig:
        return self.__load_config() if self.__config is None else self.__config

    @classmethod
    def config_class(cls) -> type[DeveloperEnvironmentConfig]:
        return DeveloperEnvironmentConfig

    @cached_property
    def config_file(self) -> Path:
        return self.storage_dirs.data.joinpath("config.json")

    def save_config(self) -> None:
        self.config_file.write_bytes(msgspec.json.encode(self.config))

    def remove_config(self) -> None:
        self.config_file.unlink()

    def __load_config(self) -> DeveloperEnvironmentConfig:
        if not self.config_file.exists():
            return self.config_class()()

        return msgspec.json.decode(self.config_file.read_bytes(), type=self.config_class())
