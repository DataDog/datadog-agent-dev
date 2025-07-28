# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Any, NoReturn

import msgspec

from dda.env.qa.interface import QAEnvironmentConfig, QAEnvironmentInterface

if TYPE_CHECKING:
    from dda.env.docker import Docker
    from dda.env.models import EnvironmentMetadata, EnvironmentStatus


class LinuxContainerConfig(QAEnvironmentConfig):
    image: Annotated[
        str,
        msgspec.Meta(
            extra={
                "help": "The container image to use",
            }
        ),
    ] = "datadog/agent"
    pull: Annotated[
        bool,
        msgspec.Meta(
            extra={
                "help": "Whether to pull the image before every container creation",
            }
        ),
    ] = False
    network: Annotated[
        str,
        msgspec.Meta(
            extra={
                "help": (
                    "The network to use for the container. Linux defaults to `host` while other platforms default "
                    "to only using port mappings"
                ),
            }
        ),
    ] = ""
    cli: Annotated[
        str,
        msgspec.Meta(
            extra={
                "help": "The name or absolute path of the container manager e.g. `docker` or `podman`",
            }
        ),
    ] = "docker"
    arch: Annotated[
        str | None,
        msgspec.Meta(
            extra={
                "help": "The architecture to use e.g. `amd64` or `arm64`",
            }
        ),
    ] = None


class LinuxContainer(QAEnvironmentInterface[LinuxContainerConfig]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__latest_status: EnvironmentStatus | None = None

    @classmethod
    def config_class(cls) -> type[LinuxContainerConfig]:
        return LinuxContainerConfig

    def start(self) -> None:
        from dda.env.models import EnvironmentState

        status = self.__latest_status if self.__latest_status is not None else self.status()
        if status.state == EnvironmentState.STOPPED:
            self.__start_from_stopped()
            return

        self.__start_anew()

    def __start_from_stopped(self) -> None:
        self.docker.wait(["start", self.container_name], message=f"Starting container: {self.container_name}")

    def __start_anew(self) -> None:
        from dda.env.models import (
            EnvironmentMetadata,
            EnvironmentNetworkMetadata,
            EnvironmentPort,
            EnvironmentPortMetadata,
        )

        if self.config.e2e:
            self.app.abort(f"The `{self.name}` QA environment does not support the `e2e` option")

        from dda.utils.agent.config.format import agent_config_to_env_vars
        from dda.utils.container.model import Mount
        from dda.utils.network.hostname import get_hostname
        from dda.utils.platform import PLATFORM_ID
        from dda.utils.process import EnvVars
        from dda.utils.retry import wait_for

        if self.config.pull:
            pull_command = ["pull", self.config.image]
            if self.config.arch is not None:
                pull_command.extend(("--platform", f"linux/{self.config.arch}"))
            self.docker.wait(pull_command, message=f"Pulling image: {self.config.image}")

        command = [
            "run",
            "-d",
            "--name",
            self.container_name,
        ]
        if self.config.arch is not None:
            command.extend(("--platform", f"linux/{self.config.arch}"))

        # Mounts
        mounts = [
            Mount(
                type="bind",
                path="/host/proc",
                source="/proc",
            )
        ]
        mounts.extend(
            Mount(
                type="bind",
                path=f"/etc/datadog-agent/conf.d/{integration}.d",
                source=str(self.agent_config.integrations_dir / integration),
            )
            for integration in self.agent_config.load_integrations()
        )

        for mount in mounts:
            command.extend(("--mount", mount.as_csv()))

        ports = EnvironmentPortMetadata()
        network_metadata = EnvironmentNetworkMetadata(server="localhost", ports=ports)

        # Environment variables
        agent_config = self.agent_config.load()
        if "api_key" not in agent_config:
            self.app.display_warning("No API key set in the Agent config, using a placeholder")
            agent_config["api_key"] = "a" * 32

        agent_config["hostname"] = get_hostname()
        cmd_port = self.derive_dynamic_port("cmd")
        agent_config["cmd_port"] = str(cmd_port)
        if agent_config.get("use_dogstatsd", True):
            agent_config["dogstatsd_non_local_traffic"] = "true"
            ports.agent["dogstatsd"] = EnvironmentPort(port=self.derive_dynamic_port("dogstatsd"), protocol="udp")
            agent_config["dogstatsd_port"] = str(ports.agent["dogstatsd"].port)
        if agent_config.get("apm_config", {}).get("enabled"):
            ports.agent["apm"] = EnvironmentPort(port=self.derive_dynamic_port("apm"))
            agent_config["receiver_port"] = str(ports.agent["apm"].port)
        process_config = agent_config.get("process_config", {})
        if process_config.get("process_collection", {}).get("enabled") or process_config.get("enabled") == "true":
            ports.agent["process_expvar"] = EnvironmentPort(port=self.derive_dynamic_port("process_expvar"))
            agent_config["process_config"]["expvar_port"] = str(ports.agent["process_expvar"].port)
        if agent_config.get("expvar_port"):
            ports.agent["expvar"] = EnvironmentPort(port=self.derive_dynamic_port("expvar"))
            agent_config["expvar_port"] = str(ports.agent["expvar"].port)

        env_vars = agent_config_to_env_vars(agent_config)
        env_vars.update(self.config.env)
        for env_var in env_vars:
            command.extend(("-e", env_var))

        # Network
        if self.config.network:
            command.extend(("--network", self.config.network))
        # Host mode is only enabled by default on Linux:
        # https://docs.docker.com/engine/network/drivers/host/
        elif PLATFORM_ID == "linux":
            command.extend(("--network", "host"))
        else:
            command.extend(("-p", f"{cmd_port}:{cmd_port}"))
            for port in ports.agent.values():
                command.extend(("-p", f"{port.port}:{port.port}/{port.protocol}"))

        command.append(self.config.image)
        self.docker.wait(
            command,
            message=f"Creating and starting container: {self.container_name}",
            env=EnvVars(env_vars),
        )

        with self.app.status(f"Waiting for container: {self.container_name}"):
            wait_for(self.check_readiness, timeout=30, interval=0.3)

        self.save_metadata(EnvironmentMetadata(network=network_metadata))

    def stop(self) -> None:
        self.docker.wait(
            ["stop", self.container_name],
            message=f"Stopping container: {self.container_name}",
        )

    def restart(self) -> None:
        self.docker.wait(["restart", self.container_name], message=f"Restarting container: {self.container_name}")

    def remove(self) -> None:
        self.docker.wait(["rm", "-f", self.container_name], message=f"Removing container: {self.container_name}")

    def sync_agent_config(self) -> None:
        self.stop()
        self.remove()
        self.start()

    def status(self) -> EnvironmentStatus:
        from dda.env.models import EnvironmentState

        status = self.docker.get_status(self.container_name)
        if status.state == EnvironmentState.NONEXISTENT:
            return status

        self.__latest_status = status
        return status

    def metadata(self) -> EnvironmentMetadata:
        return self.load_metadata()

    def run_command(self, command: list[str]) -> None:
        self.docker.run(["exec", "-t", self.container_name, *command])

    def launch_shell(self) -> NoReturn:
        process = self.docker.attach(["exec", "-it", self.container_name, "bash"], check=False)
        self.app.abort(code=process.returncode)

    @cached_property
    def container_name(self) -> str:
        return f"dda-qa-{self.name}-{self.instance}"

    @cached_property
    def docker(self) -> Docker:
        from dda.env.docker import Docker

        docker = Docker(self.app)
        docker.path = self.config.cli
        return docker

    def derive_dynamic_port(self, name: str) -> int:
        from dda.utils.network.protocols import derive_dynamic_port

        return derive_dynamic_port(f"{self.container_name}-{name}")

    def check_readiness(self) -> None:
        output = self.docker.capture(["logs", self.container_name])
        if "Starting Datadog Agent v" not in output:
            raise RuntimeError
