# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Any, Literal, NoReturn

import msgspec

from dda.env.dev.interface import DeveloperEnvironmentConfig, DeveloperEnvironmentInterface

if TYPE_CHECKING:
    from dda.env.models import EnvironmentStatus
    from dda.env.shells.interface import Shell
    from dda.tools.docker import Docker
    from dda.utils.container.model import Mount


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
    arch: Annotated[
        str | None,
        msgspec.Meta(
            extra={
                "help": "The architecture to use e.g. `amd64` or `arm64`",
            }
        ),
    ] = None


class LinuxContainer(DeveloperEnvironmentInterface[LinuxContainerConfig]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__latest_status: EnvironmentStatus | None = None

    @classmethod
    def config_class(cls) -> type[LinuxContainerConfig]:
        return LinuxContainerConfig

    @cached_property
    def docker(self) -> Docker:
        from dda.tools.docker import Docker

        docker = Docker(self.app)
        docker.path = self.config.cli
        return docker

    def start(self) -> None:
        from dda.env.models import EnvironmentState

        status = self.__latest_status if self.__latest_status is not None else self.status()
        if status.state == EnvironmentState.STOPPED:
            self.docker.wait(["start", self.container_name], message=f"Starting container: {self.container_name}")
        else:
            from dda.config.constants import AppEnvVars
            from dda.utils._git import (
                GIT_AUTHOR_EMAIL_ENV_VAR,
                GIT_AUTHOR_NAME_ENV_VAR,
                get_git_author_email,
                get_git_author_name,
            )
            from dda.utils.process import EnvVars
            from dda.utils.retry import wait_for

            if not self.config.no_pull:
                pull_command = ["pull", self.config.image]
                if self.config.arch is not None:
                    pull_command.extend(("--platform", f"linux/{self.config.arch}"))
                self.docker.wait(pull_command, message=f"Pulling image: {self.config.image}")

            self.shared_dir.ensure_dir()
            command = [
                "run",
                "--pull",
                "never",
                "-d",
                "--name",
                self.container_name,
                "-p",
                f"{self.ssh_port}:22",
                "-v",
                "/var/run/docker.sock:/var/run/docker.sock",
                "-e",
                "DD_SHELL",
                "-e",
                AppEnvVars.TELEMETRY_API_KEY,
                "-e",
                GIT_AUTHOR_NAME_ENV_VAR,
                "-e",
                GIT_AUTHOR_EMAIL_ENV_VAR,
            ]
            if self.config.arch is not None:
                command.extend(("--platform", f"linux/{self.config.arch}"))

            for shared_shell_file in self.shell.collect_shared_files():
                unix_path = shared_shell_file.relative_to(self.global_shared_dir).as_posix()
                command.extend(("-v", f"{shared_shell_file}:{self.home_dir}/.shared/{unix_path}"))

            for mount in self.cache_volumes:
                command.extend(("--mount", mount.as_csv()))

            if not self.config.clone:
                from dda.utils.fs import Path

                repos_path = Path.cwd().parent
                for repo_spec in self.config.repos:
                    repo = repo_spec.split("@")[0]
                    repo_path = repos_path / repo
                    if not repo_path.is_dir():
                        self.app.abort(f"Local repository not found: {repo}")

                    command.extend(("-v", f"{repo_path}:{self.repo_path(repo)}"))

            command.append(self.config.image)

            env = EnvVars()
            env["DD_SHELL"] = self.config.shell
            if self.app.telemetry.api_key is not None:
                env[AppEnvVars.TELEMETRY_API_KEY] = self.app.telemetry.api_key

            if git_user := (self.app.config.git.user.name or get_git_author_name()):
                env[GIT_AUTHOR_NAME_ENV_VAR] = git_user

            if git_email := (self.app.config.git.user.email or get_git_author_email()):
                env[GIT_AUTHOR_EMAIL_ENV_VAR] = git_email

            self.docker.wait(
                command,
                message=f"Creating and starting container: {self.container_name}",
                env=env,
            )

            with self.app.status(f"Waiting for container: {self.container_name}"):
                wait_for(self.check_readiness, timeout=30, interval=0.3)

            self.ensure_ssh_config()

            if self.config.clone:
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
        self.docker.wait(
            ["stop", "-t", "0", self.container_name],
            message=f"Stopping container: {self.container_name}",
        )

    def remove(self) -> None:
        self.docker.wait(["rm", "-f", self.container_name], message=f"Removing container: {self.container_name}")

    def status(self) -> EnvironmentStatus:
        import json

        from dda.env.models import EnvironmentState, EnvironmentStatus

        output = self.docker.capture(["inspect", self.container_name], check=False, cross_streams=False)
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
        process = self.app.subprocess.attach(ssh_command, check=False)
        self.app.abort(code=process.returncode)

    def code(self, *, repo: str | None = None) -> None:
        self.ensure_ssh_config()
        self.app.subprocess.run(
            ["code", "--remote", f"ssh-remote+root@localhost:{self.ssh_port}", self.repo_path(repo)],
        )

    def run_command(self, command: list[str], *, repo: str | None = None) -> None:
        self.ensure_ssh_config()
        self.app.subprocess.run(self.construct_command(command, cwd=self.repo_path(repo)))

    def remove_cache(self) -> None:
        volumes = set(self.cache_volume_names())
        output = self.docker.capture(["volume", "ls", "--format", "{{.Name}}"])
        volumes.intersection_update(output.splitlines())

        if not volumes:
            return

        command = ["volume", "rm", *sorted(volumes)]
        self.docker.wait(command, message="Removing cache")

    def cache_size(self) -> int:
        import re

        from binary import BinaryUnits, convert_units

        volumes = dict.fromkeys(self.cache_volume_names(), 0)
        with self.app.status("Calculating cache size"):
            output = self.docker.capture(
                ["system", "df", "-v", "--format", '{{range .Volumes}}{{printf "%s %s" .Name .Size}}\n{{end}}'],
            )

        # 4B, 1.23MB, etc.
        size_pattern = re.compile(r"([\d.]+)(\w+)")
        for line in output.splitlines():
            name, size = line.split()
            if name in volumes and (match := size_pattern.match(size)) is not None:
                value, unit = match.groups()
                value_in_bytes = convert_units(
                    float(value),
                    unit=getattr(BinaryUnits, unit.upper()),
                    to=BinaryUnits.B,
                    exact=True,
                )[0]
                volumes[name] = int(value_in_bytes)

        return sum(volumes.values())

    @cached_property
    def hostname(self) -> str:
        return "localhost"

    @cached_property
    def ssh_port(self) -> int:
        from dda.utils.ssh import derive_dynamic_ssh_port

        return derive_dynamic_ssh_port(self.container_name)

    @cached_property
    def home_dir(self) -> str:
        return "/root"

    @cached_property
    def container_name(self) -> str:
        return f"dda-{self.name}-{self.instance}"

    @cached_property
    def shell(self) -> Shell:
        from dda.env.shells import get_shell

        return get_shell(self.config.shell)(self.global_shared_dir)

    @cached_property
    def cache_volumes(self) -> list[Mount]:
        from dda.utils.container.model import Mount

        return [
            # `go env GOCACHE`
            Mount(type="volume", path="/root/.cache/go-build", source=self.get_volume_name("go_build_cache")),
            # `go env GOMODCACHE`
            Mount(type="volume", path="/go/pkg/mod", source=self.get_volume_name("go_mod_cache")),
            # `pip cache dir`
            Mount(type="volume", path="/root/.cache/pip", source=self.get_volume_name("pip_cache")),
            # Rust
            Mount(type="volume", path="/root/.cargo/registry", source=self.get_volume_name("cargo_registry")),
            Mount(type="volume", path="/root/.cargo/git", source=self.get_volume_name("cargo_git")),
            # Omnibus
            Mount(type="volume", path="/omnibus/vendor/bundle", source=self.get_volume_name("omnibus_gems")),
            Mount(type="volume", path="/omnibus/cache", source=self.get_volume_name("omnibus_cache")),
            Mount(
                type="volume",
                path="/tmp/omnibus-git-cache",  # noqa: S108
                source=self.get_volume_name("omnibus_git_cache"),
            ),
            # VS Code/Cursor
            Mount(type="volume", path="/root/.vscode-extensions", source=self.get_volume_name("vscode_extensions")),
        ]

    def cache_volume_names(self) -> list[str]:
        return [volume.source for volume in self.cache_volumes if volume.source is not None]

    def get_volume_name(self, key: str) -> str:
        name = f"dda-env-dev-{self.name}-{key}"
        if self.config.arch is not None:
            name += f"-{self.config.arch}"
        return name

    def construct_command(self, command: list[str], *, cwd: str | None = None) -> list[str]:
        if cwd is None:
            cwd = self.home_dir

        ssh_command = self.ssh_base_command()
        ssh_command.append(self.shell.format_command(command, cwd=cwd))
        return ssh_command

    def check_readiness(self) -> None:
        output = self.docker.capture(["logs", self.container_name])
        if "Server listening on :: port 22" not in output:
            raise RuntimeError

    def ssh_base_command(self) -> list[str]:
        from dda.utils.ssh import ssh_base_command

        return ssh_base_command("root@localhost", self.ssh_port)

    def ensure_ssh_config(self) -> None:
        from dda.env.ssh import ensure_ssh_config

        return ensure_ssh_config(self.hostname)

    def repo_path(self, repo: str | None) -> str:
        if repo is None:
            repo = self.default_repo

        return f"{self.home_dir}/repos/{repo}"
