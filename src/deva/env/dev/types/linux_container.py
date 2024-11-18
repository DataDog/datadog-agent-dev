# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Any, Literal, NoReturn

import msgspec  # noqa: TCH002

from deva.env.dev.interface import DeveloperEnvironmentConfig, DeveloperEnvironmentInterface

if TYPE_CHECKING:
    from deva.env.models import EnvironmentStatus
    from deva.env.shells.interface import Shell


class LinuxContainerConfig(DeveloperEnvironmentConfig):
    image: Annotated[
        str,
        msgspec.Meta(
            extra={
                "help": "The container image to use",
            }
        ),
    ] = "datadog/agent-dev-env-linux"
    no_pull: Annotated[
        bool,
        msgspec.Meta(
            extra={
                "help": "Prevent pulling the image before every container creation",
            }
        ),
    ] = False
    cli: Annotated[
        str,
        msgspec.Meta(
            extra={
                "help": "The name or absolute path of the container manager e.g. `docker` or `podman`",
            }
        ),
    ] = "docker"
    shell: Annotated[
        Literal["bash", "nu", "zsh"],
        msgspec.Meta(
            extra={
                "help": "The name of the shell to use e.g. `zsh` or `nu`",
            }
        ),
    ] = "zsh"


class LinuxContainer(DeveloperEnvironmentInterface[LinuxContainerConfig]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__latest_status: EnvironmentStatus | None = None

    @classmethod
    def config_class(cls) -> type[LinuxContainerConfig]:
        return LinuxContainerConfig

    def start(self) -> None:
        from deva.env.models import EnvironmentState

        status = self.__latest_status if self.__latest_status is not None else self.status()
        if status.state == EnvironmentState.STOPPED:
            self.app.subprocess.wait(
                [self.config.cli, "start", self.container_name], message=f"Starting container: {self.container_name}"
            )
        else:
            from deva.utils.retry import wait_for

            if not self.config.no_pull:
                self.app.subprocess.wait(
                    [self.config.cli, "pull", self.config.image], message=f"Pulling image: {self.config.image}"
                )

            self.shared_dir.ensure_dir()
            command = [
                self.config.cli,
                "run",
                "--pull",
                "never",
                "-d",
                "--name",
                self.container_name,
                "-p",
                f"{self.ssh_port}:22",
                "-e",
                f"DD_SHELL={self.config.shell}",
            ]
            for shared_shell_file in self.shell.collect_shared_files():
                unix_path = shared_shell_file.relative_to(self.global_shared_dir).as_posix()
                command.extend(("-v", f"{shared_shell_file}:{self.home_dir}/.shared/{unix_path}"))

            command.append(self.config.image)
            self.app.subprocess.wait(command, message=f"Creating and starting container: {self.container_name}")

            with self.app.status(self.app.style_waiting(f"Waiting for container: {self.container_name}")):
                wait_for(self.check_readiness, timeout=30, wait=0.3)

            self.ensure_ssh_config()

            for repo_spec in self.config.repos:
                repo, _, ref = repo_spec.partition("@")
                if ref:
                    clone_command = ["git", "dd-clone", repo, ref]
                    wait_message = f"Cloning repository: {repo}@{ref}"
                else:
                    clone_command = ["git", "dd-clone", repo]
                    wait_message = f"Cloning repository: {repo}"

                self.app.subprocess.wait(self.construct_command(clone_command), message=wait_message)

    def stop(self) -> None:
        self.app.subprocess.wait(
            [self.config.cli, "stop", "-t", "0", self.container_name],
            message=f"Stopping container: {self.container_name}",
        )

    def remove(self) -> None:
        self.app.subprocess.wait(
            [self.config.cli, "rm", "-f", self.container_name], message=f"Removing container: {self.container_name}"
        )

    def status(self) -> EnvironmentStatus:
        import json

        from deva.env.models import EnvironmentState, EnvironmentStatus

        output = self.app.subprocess.capture(
            [self.config.cli, "inspect", self.container_name], check=False, cross_streams=False
        )
        items = json.loads(output)
        if not items:
            return EnvironmentStatus(state=EnvironmentState.NONEXISTENT)

        inspection = items[0]

        # https://docs.docker.com/reference/api/engine/version/v1.47/#tag/Container/operation/ContainerList
        # https://docs.podman.io/en/latest/_static/api.html?version=v5.0#tag/containers-(compat)/operation/ContainerList
        state_data = inspection["State"]
        status = state_data["Status"].lower()
        if status == "running":
            state = EnvironmentState.STARTED
        elif status in {"created", "paused"}:
            state = EnvironmentState.STOPPED
        elif status == "exited":
            state = EnvironmentState.ERROR if state_data["ExitCode"] == 1 else EnvironmentState.STOPPED
        elif status == "restarting":
            state = EnvironmentState.STARTING
        elif status == "removing":
            state = EnvironmentState.STOPPING
        else:
            state = EnvironmentState.UNKNOWN

        status = EnvironmentStatus(state=state)
        self.__latest_status = status
        return status

    def launch_shell(self, *, repo: str | None = None) -> NoReturn:
        self.ensure_ssh_config()
        ssh_command = self.ssh_base_command()
        ssh_command.append(self.shell.get_login_command(cwd=self.repo_path(repo)))
        self.app.subprocess.replace_current_process(ssh_command)

    def code(self, *, repo: str | None = None) -> None:
        self.ensure_ssh_config()
        self.app.subprocess.run(
            ["code", "--remote", f"ssh-remote+root@localhost:{self.ssh_port}", self.repo_path(repo)],
        )

    def run_command(self, command: list[str], *, repo: str | None = None) -> None:
        self.ensure_ssh_config()
        self.app.subprocess.run(self.construct_command(command, cwd=self.repo_path(repo)))

    @cached_property
    def hostname(self) -> str:
        return "localhost"

    @cached_property
    def ssh_port(self) -> int:
        from deva.utils.ssh import derive_dynamic_ssh_port

        return derive_dynamic_ssh_port(self.container_name)

    @cached_property
    def home_dir(self) -> str:
        return "/root"

    @cached_property
    def container_name(self) -> str:
        return f"deva-{self.name}-{self.instance}"

    @cached_property
    def shell(self) -> Shell:
        from deva.env.shells import get_shell

        return get_shell(self.config.shell)(self.global_shared_dir)

    def construct_command(self, command: list[str], *, cwd: str | None = None) -> list[str]:
        if cwd is None:
            cwd = self.home_dir

        ssh_command = self.ssh_base_command()
        ssh_command.append(self.shell.format_command(command, cwd=cwd))
        return ssh_command

    def check_readiness(self) -> bool:
        output = self.app.subprocess.capture([self.config.cli, "logs", self.container_name])
        return "Server listening on :: port 22" in output

    def ssh_base_command(self) -> list[str]:
        from deva.utils.ssh import ssh_base_command

        return ssh_base_command("root@localhost", self.ssh_port)

    def ensure_ssh_config(self) -> None:
        from deva.env.ssh import ensure_ssh_config

        return ensure_ssh_config(self.hostname)

    def repo_path(self, repo: str | None) -> str:
        if repo is None:
            repo = self.default_repo

        return f"{self.home_dir}/repos/{repo}"
