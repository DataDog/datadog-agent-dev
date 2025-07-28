# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Generic, NoReturn, cast

import msgspec

if TYPE_CHECKING:
    from dda.env.config.agent import AgentConfig


class QAEnvironmentConfig(msgspec.Struct, kw_only=True):
    env: Annotated[
        dict[str, str],
        msgspec.Meta(
            extra={
                "params": ["-e", "--env"],
                "help": "Extra environment variables to expose at Agent startup",
            }
        ),
    ] = {}
    e2e: Annotated[
        bool,
        msgspec.Meta(
            extra={
                "help": "Whether to run the mock intake service for testing",
            }
        ),
    ] = False


if TYPE_CHECKING:
    from typing_extensions import TypeVar

    from dda.cli.application import Application
    from dda.config.model.storage import StorageDirs
    from dda.env.models import EnvironmentMetadata, EnvironmentStatus
    from dda.utils.fs import Path

    ConfigT = TypeVar("ConfigT", bound=QAEnvironmentConfig, default=QAEnvironmentConfig)
else:
    from typing import TypeVar

    ConfigT = TypeVar("ConfigT")


class QAEnvironmentInterface(ABC, Generic[ConfigT]):
    """
    This interface defines the behavior of a QA environment.
    """

    def __init__(
        self,
        *,
        app: Application,
        name: str,
        instance: str,
        config: ConfigT | None = None,
        agent_config_template_path: Path | None = None,
    ) -> None:
        self.__app = app
        self.__name = name
        self.__instance = instance
        self.__config = config
        self.__agent_config_template_path = agent_config_template_path

    @abstractmethod
    def start(self) -> None:
        """
        This method starts the QA environment. If this method returns early, the environment's
        [status][dda.env.qa.interface.QAEnvironmentInterface.status] should contain information
        about the startup progress.

        This method will only be called if the environment's
        [status][dda.env.qa.interface.QAEnvironmentInterface.status] is
        [stopped][dda.env.models.EnvironmentState.STOPPED] or
        [nonexistent][dda.env.models.EnvironmentState.NONEXISTENT].

        Users trigger this method by running the [`env qa start`](../../../cli/commands.md#dda-env-qa-start) command.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        This method stops the QA environment. If this method returns early, the environment's
        [status][dda.env.qa.interface.QAEnvironmentInterface.status] should contain information
        about the shutdown progress.

        This method will only be called if the environment's
        [status][dda.env.qa.interface.QAEnvironmentInterface.status] is
        [started][dda.env.models.EnvironmentState.STARTED].

        Users trigger this method by running the [`env qa stop`](../../../cli/commands.md#dda-env-qa-stop) command.
        """

    @abstractmethod
    def restart(self) -> None:
        """
        This method restarts the QA environment and must only return when the environment is fully restarted.

        This method will only be called if the environment's
        [status][dda.env.qa.interface.QAEnvironmentInterface.status] is
        [started][dda.env.models.EnvironmentState.STARTED].

        Users trigger this method by running the [`env qa restart`](../../../cli/commands.md#dda-env-qa-restart)
        command.
        """

    @abstractmethod
    def remove(self) -> None:
        """
        This method removes the QA environment and all associated state.

        This method will only be called if the environment's
        [status][dda.env.qa.interface.QAEnvironmentInterface.status] is
        [stopped][dda.env.models.EnvironmentState.STOPPED] or in an
        [error][dda.env.models.EnvironmentState.ERROR] state.

        Users trigger this method by running the [`env qa remove`](../../../cli/commands.md#dda-env-qa-remove)
        command or with the `-r`/`--remove` flag of the [`env qa stop`](../../../cli/commands.md#dda-env-qa-stop)
        command.
        """

    @abstractmethod
    def status(self) -> EnvironmentStatus:
        """
        This method returns the current status of the QA environment.
        """

    @abstractmethod
    def metadata(self) -> EnvironmentMetadata:
        """
        This method returns metadata about the QA environment.
        """

    @abstractmethod
    def run_command(self, command: list[str]) -> None:
        """
        This method runs a command inside the QA environment.

        Users trigger this method by running the [`env qa run`](../../../cli/commands.md#dda-env-qa-run) command.

        Parameters:
            command: The command to run inside the developer environment.
        """

    @abstractmethod
    def sync_agent_config(self) -> None:
        """
        This method ensures that the QA environment's Agent is configured with the current state of the host's
        [Agent configuration directory][dda.env.qa.interface.QAEnvironmentInterface.agent_config_dir]. For
        containerized environments, this usually requires restarting the container itself.

        Users trigger this method by running the [`env qa config sync`](../../../cli/commands.md#dda-env-qa-config-sync)
        command.
        """

    def launch_shell(self) -> NoReturn:
        """
        This method starts an interactive shell inside the QA environment.

        Users trigger this method by running the [`env qa shell`](../../../cli/commands.md#dda-env-qa-shell) command.
        """
        raise NotImplementedError

    def launch_gui(self) -> NoReturn:
        """
        This method starts an interactive GUI inside the QA environment using e.g. RDP or VNC.

        Users trigger this method by running the [`env qa gui`](../../../cli/commands.md#dda-env-qa-gui) command.
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
        return self.app.config.storage.join("env", "qa", self.name, self.instance)

    @cached_property
    def state_dir(self) -> Path:
        """
        The directory that is used to persist the environment's state. This directory will always be deleted after the
        environment is removed with the [`env qa remove`](../../../cli/commands.md#dda-env-qa-remove) command or with
        the [`env qa stop`](../../../cli/commands.md#dda-env-qa-stop) command when the `-r`/`--remove` flag is used.
        """
        return self.storage_dirs.data / ".state"

    @cached_property
    def config(self) -> ConfigT:
        """
        The user-defined configuration as an instance of the
        [`QAEnvironmentConfig`][dda.env.qa.interface.QAEnvironmentConfig] class, or subclass thereof.
        """
        return self.__load_config() if self.__config is None else self.__config

    @classmethod
    def config_class(cls) -> type[QAEnvironmentConfig]:
        """
        The [`QAEnvironmentConfig`][dda.env.qa.interface.QAEnvironmentConfig] class, or subclass thereof,
        that is used to configure the environment.
        """
        return QAEnvironmentConfig

    @cached_property
    def config_file(self) -> Path:
        """
        The path to the JSON file that is used to persist the environment's configuration until the environment
        is [removed][dda.env.qa.interface.QAEnvironmentInterface.remove].
        """
        return self.state_dir / "config.json"

    @cached_property
    def metadata_file(self) -> Path:
        """
        The path to the JSON file that is used to persist the environment's metadata until the environment
        is [removed][dda.env.qa.interface.QAEnvironmentInterface.remove].
        """
        return self.state_dir / "metadata.json"

    @cached_property
    def agent_config_dir(self) -> Path:
        """
        The path to the directory that is used to persist the environment's Agent configuration.

        Users can find the location by running the
        [`env qa config find`](../../../cli/commands.md#dda-env-qa-config-find) or
        [`env qa config explore`](../../../cli/commands.md#dda-env-qa-config-explore) commands.
        """
        return self.state_dir / "agent_config"

    @cached_property
    def agent_config(self) -> AgentConfig:
        from dda.env.config.agent import AgentConfig

        return AgentConfig(app=self.app, path=self.agent_config_dir)

    def save_metadata(self, metadata: EnvironmentMetadata) -> None:
        self.metadata_file.write_bytes(msgspec.json.encode(metadata))

    def load_metadata(self) -> EnvironmentMetadata:
        from dda.env.models import EnvironmentMetadata

        return msgspec.json.decode(self.metadata_file.read_bytes(), type=EnvironmentMetadata)

    def save_state(self) -> None:
        import shutil

        self.config_file.parent.ensure_dir()
        self.config_file.write_bytes(msgspec.json.encode(self.config))

        if self.agent_config_dir.is_dir():
            shutil.rmtree(self.agent_config_dir)

        if self.__agent_config_template_path:
            shutil.copytree(self.__agent_config_template_path, self.agent_config_dir)

    def remove_state(self) -> None:
        if self.state_dir.is_dir():
            import shutil

            shutil.rmtree(self.state_dir)

    def __load_config(self) -> ConfigT:
        config = (
            msgspec.json.decode(self.config_file.read_bytes(), type=self.config_class())
            if self.config_file.is_file()
            else self.config_class()()
        )
        return cast(ConfigT, config)
