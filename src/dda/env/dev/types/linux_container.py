# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Any, Literal, NoReturn

import msgspec

from dda.env.dev.interface import DeveloperEnvironmentConfig, DeveloperEnvironmentInterface
from dda.utils.fs import cp_r, temp_directory
from dda.utils.git.constants import GitEnvVars

if TYPE_CHECKING:
    from dda.env.models import EnvironmentStatus
    from dda.env.shells.interface import Shell
    from dda.tools.docker import Docker
    from dda.utils.container.model import Mount
    from dda.utils.editors.interface import EditorInterface
    from dda.utils.fs import Path


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
    # This parameter stores the raw volume specifications as provided by the user.
    # Use the `extra_mounts` property to get the list of extra mounts as Mount objects.
    extra_volume_specs: Annotated[
        list[str],
        msgspec.Meta(
            extra={
                "params": ["-v", "--volume"],
                "help": (
                    """\
Additional host directories to be mounted into the dev env. This option may be supplied multiple
times, and has the same syntax as the `-v/--volume` flag of `docker run`. Examples:

- `./some-repo:/root/repos/some-repo`
- `/tmp/some-location:/location:ro`
- `~/projects:/root/projects:ro`
"""
                ),
            }
        ),
    ] = msgspec.field(default_factory=list)
    extra_mount_specs: Annotated[
        list[str],
        msgspec.Meta(
            extra={
                "params": ["-m", "--mount"],
                "help": (
                    """\
Additional mounts to be added to the dev env. These can be either bind mounts from the host or Docker volume mounts.
This option may be supplied multiple times, and has the same syntax as the `-m/--mount` flag of `docker run`. Examples:

- `type=bind,src=/tmp/some-location,dst=/location`
- `type=volume,src=some-volume,dst=/location`
- `type=bind,src=/tmp/some-location,dst=/location,bind-propagation=rslave`
"""
                ),
            }
        ),
    ] = msgspec.field(default_factory=list)


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
                "-p",
                f"{self.mcp_port}:9000",
                "-v",
                "/var/run/docker.sock:/var/run/docker.sock",
            ]
            if sys.platform != "win32":
                command.extend((
                    "-e",
                    f"HOST_UID={os.getuid()}",
                    "-e",
                    f"HOST_GID={os.getgid()}",
                ))

            command.extend((
                "-e",
                "DD_SHELL",
                "-e",
                AppEnvVars.TELEMETRY_API_KEY,
                "-e",
                AppEnvVars.TELEMETRY_USER_MACHINE_ID,
                "-e",
                GitEnvVars.AUTHOR_NAME,
                "-e",
                GitEnvVars.AUTHOR_EMAIL,
            ))
            if self.config.arch is not None:
                command.extend(("--platform", f"linux/{self.config.arch}"))

            command.extend(("-v", f"{self.shared_dir}:/.shared"))

            for shared_shell_file in self.shell.collect_shared_files():
                unix_path = shared_shell_file.relative_to(self.global_shared_dir).as_posix()
                command.extend(("-v", f"{shared_shell_file}:{self.home_dir}/.shared/{unix_path}"))

            for mount in self.cache_volumes:
                command.extend(("--mount", mount.as_csv()))

            if not self.config.clone:
                for repo_spec in self.config.repos:
                    repo = repo_spec.split("@")[0]
                    repo_path = self._resolve_repository_path(repo_spec)
                    command.extend(("-v", f"{repo_path}:{self.repo_path(repo)}"))

            for mount_spec in self.config.extra_mount_specs:
                command.extend(("--mount", mount_spec))

            for volume_spec in self.config.extra_volume_specs:
                command.extend(("--volume", volume_spec))

            command.append(self.config.image)

            env = EnvVars()
            env["DD_SHELL"] = self.config.shell
            env[AppEnvVars.TELEMETRY_USER_MACHINE_ID] = self.app.telemetry.user.machine_id
            if self.app.telemetry.api_key is not None:
                env[AppEnvVars.TELEMETRY_API_KEY] = self.app.telemetry.api_key
            if self.app.config.tools.git.author.name:
                env[GitEnvVars.AUTHOR_NAME] = self.app.config.tools.git.author.name
            if self.app.config.tools.git.author.email:
                env[GitEnvVars.AUTHOR_EMAIL] = self.app.config.tools.git.author.email

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

        output = self.docker.capture(["inspect", self.container_name], check=False)
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

    def code(self, *, editor: EditorInterface, repo: str | None = None) -> None:
        if editor.name not in {"vscode", "cursor"}:
            self.app.abort(f"Unsupported editor: {editor.name}")

        self.ensure_ssh_config()
        repo_path = self.repo_path(repo)

        # TODO: Currently, we do not support aggregating local commands from multiple repositories as a single tool
        #       so we assume for the purposes of MCP that only one repository is open at a time. We should extend
        #       the MCP server to support multiple repositories. Documentation for extending the MCP server is here:
        #       https://ofek.dev/pycli-mcp/api/
        self.app.subprocess.wait(
            self.construct_command(["dda", "self", "mcp-server", "stop"], cwd=repo_path),
            message="Stopping MCP server",
        )
        self.app.subprocess.wait(
            self.construct_command(["dda", "self", "mcp-server", "start"], cwd=repo_path),
            message="Starting MCP server",
        )

        editor.open_via_ssh(server=self.hostname, port=self.ssh_port, path=repo_path)

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
        from dda.utils.network.protocols import derive_dynamic_port

        return derive_dynamic_port(f"{self.container_name}-ssh")

    @cached_property
    def mcp_port(self) -> int:
        from dda.utils.network.protocols import derive_dynamic_port

        return derive_dynamic_port(f"{self.container_name}-mcp")

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
            # `uv cache dir`
            Mount(type="volume", path="/root/.cache/uv", source=self.get_volume_name("uv_cache")),
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
        # The `docker logs` command outputs to stderr
        output = self.docker.capture(["logs", self.container_name], cross_streams=True)
        if "Server listening on :: port 22" not in output:
            msg = f"Container `{self.container_name}` is not ready: {output}"
            raise RuntimeError(msg)

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

    def _resolve_repository_path(self, repo_spec: str) -> Path:
        """
        Resolve the local path for a repository specification.

        Tries multiple strategies:
        1. Check if current directory is the requested repo (git-aware, handles worktrees)
        2. Check parent directory for repo (backward compatible)

        Args:
            repo_spec: Repository specification (e.g., "datadog-agent" or "datadog-agent@branch")

        Returns:
            Path to the repository

        Raises:
            Aborts if repository cannot be found
        """
        from dda.utils.fs import Path

        repo_name = repo_spec.split("@")[0]  # Strip @branch/@tag if present

        # Strategy 1: Check if current directory is a git repository matching the repo name
        cwd = Path.cwd()
        if self._is_matching_repository(cwd, repo_name):
            return cwd

        # Strategy 2: Check parent directory (existing behavior, backward compatible)
        parent_repo_path = cwd.parent / repo_name
        if parent_repo_path.is_dir():
            if self._is_matching_repository(parent_repo_path, repo_name):
                return parent_repo_path
            # Fallback: If not a git repo but directory exists, use it for backward compat
            return parent_repo_path

        self.app.abort(f"Local repository not found: {repo_name}")  # noqa: RET503

    def _is_matching_repository(self, path: Path, expected_repo_name: str) -> bool:
        """
        Check if the given path is a git repository matching the expected repository name.

        Uses git remote URL to determine the repository name, which works for:
        - Regular repositories
        - Git worktrees (regardless of directory name)
        - Nested repository structures

        Args:
            path: Path to check
            expected_repo_name: Expected repository name (e.g., "datadog-agent")

        Returns:
            True if the path is a git repository matching the expected name
        """
        if not path.is_dir():
            return False

        git_dir = path / ".git"
        if not git_dir.exists():
            return False

        # Use git to get the repository name from the remote URL
        try:
            # Change to the target directory temporarily to get its remote
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(path)
                remote = self.app.tools.git.get_remote()
                return remote.repo == expected_repo_name
            finally:
                os.chdir(original_cwd)
        except Exception:  # noqa: BLE001
            # Not a git repository or no remote configured
            return False

    def _container_cp(self, source: str, destination: str, *args: Any) -> None:
        """Runs a `cp -r` command inside the context of the container"""
        self.run_command(["cp", "-r", f'"{source}"', f'"{destination}"', *args])

    def _container_mv(self, source: str, destination: str, *args: Any) -> None:
        """Runs a `mv` command inside the context of the container"""
        self.run_command(["mv", f'"{source}"', f'"{destination}"', *args])

    def export_path(
        self,
        source: str,
        destination: Path,
    ) -> None:
        from os.path import basename
        from shutil import move

        # 0. Ensure that both paths are absolute, knowing source represents a path in the container
        if not source.startswith("/"):
            msg = "source must be an absolute path in the container filesystem"
            raise ValueError(msg)

        destination = destination.resolve()

        # 1. Create a temporary directory within the shared directory
        with temp_directory(self.shared_dir) as wd:
            # 2. Run `cp -r` inside the container to copy from inside the container into that shared directory
            # NOTE: When running `cp -r folder1 folder2`, the _contents_ of `folder1` are copied into `folder2`
            # We want instead to copy such that `folder1` is moved into `folder2`: `folder2/folder1`
            # To accomplish this, we explicitly add the basename of the source to the destination
            self._container_cp(source, f"/.shared/{wd.name}/{basename(source)}")
            # 3. shutil.move that source into the final destination
            move(wd / basename(source), destination)

    def import_path(
        self,
        source: Path,
        destination: str,
    ) -> None:
        # 0. Ensure that both paths are absolute, knowing destination represents a path in the container
        if not destination.startswith("/"):
            msg = "destination must be an absolute path in the container filesystem"
            raise ValueError(msg)

        source = source.resolve()

        # 1. Create a temporary directory within the shared directory
        with temp_directory(self.shared_dir) as wd:
            # 2. Copy the source into the temporary directory using cp_r
            # NOTE: Same as above, we add the basename to the destination so it works as expected with directories
            cp_r(source, wd / source.name)
            # 3. mv from the shared directory into the final destination inside the container
            self._container_mv(f"/.shared/{wd.name}/{source.name}", destination)
