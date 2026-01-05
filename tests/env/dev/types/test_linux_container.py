# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import contextmanager
from subprocess import CompletedProcess

import msgspec
import pytest

from dda.config.constants import AppEnvVars
from dda.env.dev.types.linux_container import LinuxContainer
from dda.env.models import EnvironmentState, EnvironmentStatus
from dda.utils.fs import Path
from dda.utils.git.constants import GitEnvVars

pytestmark = [pytest.mark.usefixtures("private_storage")]


@pytest.fixture(autouse=True)
def updated_config(config_file):
    # Allow Windows users to run these tests
    if sys.platform == "win32":
        config_file.data["env"] = {"dev": {"default-type": "linux-container"}}
        config_file.save()


@pytest.fixture(scope="module")
def host_user_args():
    return [] if sys.platform == "win32" else ["-e", f"HOST_UID={os.getuid()}", "-e", f"HOST_GID={os.getgid()}"]


def get_starship_mount(global_shared_dir: Path) -> list[str]:
    starship_config_file = Path.home() / ".config" / "starship.toml"
    if not starship_config_file.exists():
        return []

    return ["-v", f"{global_shared_dir / 'shell' / 'starship.toml'}:/root/.shared/shell/starship.toml"]


def get_cache_volumes() -> list[str]:
    return [
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-go_build_cache,dst=/root/.cache/go-build",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-go_mod_cache,dst=/go/pkg/mod",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-pip_cache,dst=/root/.cache/pip",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-uv_cache,dst=/root/.cache/uv",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-cargo_registry,dst=/root/.cargo/registry",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-cargo_git,dst=/root/.cargo/git",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-omnibus_gems,dst=/omnibus/vendor/bundle",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-omnibus_cache,dst=/omnibus/cache",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-omnibus_git_cache,dst=/tmp/omnibus-git-cache",
        "--mount",
        "type=volume,src=dda-env-dev-linux-container-vscode_extensions,dst=/root/.vscode-extensions",
    ]


def assert_ssh_config_written(method, hostname):
    method.assert_called_once_with(
        hostname,
        {
            "StrictHostKeyChecking": "no",
            "ForwardAgent": "yes",
            "UserKnownHostsFile": "/dev/null",
            "SetEnv": ["TERM=xterm-256color"],
        },
    )


def test_default_config(app):
    container = LinuxContainer(app=app, name="linux-container", instance="default")

    assert msgspec.to_builtins(container.config) == {
        "arch": None,
        "cli": "docker",
        "clone": False,
        "image": "datadog/agent-dev-env-linux",
        "no_pull": False,
        "repos": ["datadog-agent"],
        "shell": "zsh",
        "extra_volume_specs": [],
        "extra_mount_specs": [],
    }


class TestStatus:
    def test_default(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))
        result = dda("env", "dev", "status")
        result.check(
            exit_code=0,
            stdout=helpers.dedent(
                """
                State: nonexistent
                """
            ),
        )

    @pytest.mark.parametrize(
        ("state", "data"),
        [
            pytest.param("started", {"Status": "running"}, id="running"),
            pytest.param("stopped", {"Status": "created"}, id="created"),
            pytest.param("stopped", {"Status": "paused"}, id="paused"),
            pytest.param("stopped", {"Status": "exited", "ExitCode": 0}, id="exited without error"),
            pytest.param("error", {"Status": "exited", "ExitCode": 1}, id="exited with error"),
            pytest.param("starting", {"Status": "restarting"}, id="restarting"),
            pytest.param("stopping", {"Status": "removing"}, id="removing"),
            pytest.param("unknown", {"Status": "foo"}, id="unknown"),
        ],
    )
    def test_states(self, dda, helpers, mocker, state, data):
        mocker.patch(
            "subprocess.run",
            return_value=CompletedProcess([], returncode=0, stdout=json.dumps([{"State": data}])),
        )
        result = dda("env", "dev", "status")
        result.check(
            exit_code=0,
            stdout=helpers.dedent(
                f"""
                State: {state}
                """
            ),
        )


class TestStart:
    def test_already_started(self, dda, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "dev", "start")

        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot start developer environment `linux-container` in state `started`, must be one of: nonexistent, stopped
                """
            ),
        )

    def test_default(self, dda, helpers, mocker, temp_dir, host_user_args):
        repos_dir = temp_dir / "repos"
        repos_dir.ensure_dir()
        repo_dir = repos_dir / "datadog-agent"
        repo_dir.ensure_dir()

        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        with (
            repo_dir.as_cwd(),
            helpers.hybrid_patch(
                "subprocess.run",
                return_values={
                    # Start command checks the status
                    1: CompletedProcess([], returncode=0, stdout="{}"),
                    # Start method checks the status
                    2: CompletedProcess([], returncode=0, stdout="{}"),
                    # Capture image pull
                    # Capture container run
                    # Readiness check
                    5: CompletedProcess([], returncode=0, stdout="Server listening on :: port 22"),
                },
            ) as calls,
        ):
            result = dda("env", "dev", "start")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Pulling image: datadog/agent-dev-env-linux
                Creating and starting container: dda-linux-container-default
                Waiting for container: dda-linux-container-default
                """
            ),
        )

        assert_ssh_config_written(write_server_config, "localhost")

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / "default" / ".shared"
        global_shared_dir = shared_dir.parent.parent / ".shared"
        starship_mount = get_starship_mount(global_shared_dir)
        cache_volumes = get_cache_volumes()
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "--pull",
                        "never",
                        "-d",
                        "--name",
                        "dda-linux-container-default",
                        "-p",
                        "61938:22",
                        "-p",
                        "50069:9000",
                        "-v",
                        "/var/run/docker.sock:/var/run/docker.sock",
                        *host_user_args,
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
                        "-v",
                        f"{shared_dir}:/.shared",
                        *starship_mount,
                        "-v",
                        f"{global_shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        *cache_volumes,
                        "-v",
                        f"{repo_dir}:/root/repos/datadog-agent",
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]

    def test_clone(self, dda, helpers, mocker, temp_dir, host_user_args):
        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # Capture image pull
                # Capture container run
                # Readiness check
                5: CompletedProcess([], returncode=0, stdout="Server listening on :: port 22"),
                # Capture repo cloning
            },
        ) as calls:
            result = dda("env", "dev", "start", "--clone")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Pulling image: datadog/agent-dev-env-linux
                Creating and starting container: dda-linux-container-default
                Waiting for container: dda-linux-container-default
                Cloning repository: datadog-agent
                """
            ),
        )

        assert_ssh_config_written(write_server_config, "localhost")

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / "default" / ".shared"
        global_shared_dir = shared_dir.parent.parent / ".shared"
        starship_mount = get_starship_mount(global_shared_dir)
        cache_volumes = get_cache_volumes()
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "--pull",
                        "never",
                        "-d",
                        "--name",
                        "dda-linux-container-default",
                        "-p",
                        "61938:22",
                        "-p",
                        "50069:9000",
                        "-v",
                        "/var/run/docker.sock:/var/run/docker.sock",
                        *host_user_args,
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
                        "-v",
                        f"{shared_dir}:/.shared",
                        *starship_mount,
                        "-v",
                        f"{global_shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        *cache_volumes,
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("ssh"),
                        "-A",
                        "-q",
                        "-t",
                        "-p",
                        "61938",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone datadog-agent",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE},
            ),
        ]

    def test_no_pull(self, dda, helpers, mocker, temp_dir, host_user_args):
        repos_dir = temp_dir / "repos"
        repos_dir.ensure_dir()
        repo_dir = repos_dir / "datadog-agent"
        repo_dir.ensure_dir()

        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        with (
            repo_dir.as_cwd(),
            helpers.hybrid_patch(
                "subprocess.run",
                return_values={
                    # Start command checks the status
                    1: CompletedProcess([], returncode=0, stdout="{}"),
                    # Start method checks the status
                    2: CompletedProcess([], returncode=0, stdout="{}"),
                    # Capture container run
                    # Readiness check
                    4: CompletedProcess([], returncode=0, stdout="Server listening on :: port 22"),
                },
            ) as calls,
        ):
            result = dda("env", "dev", "start", "--no-pull")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Creating and starting container: dda-linux-container-default
                Waiting for container: dda-linux-container-default
                """
            ),
        )

        assert_ssh_config_written(write_server_config, "localhost")

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / "default" / ".shared"
        global_shared_dir = shared_dir.parent.parent / ".shared"
        starship_mount = get_starship_mount(global_shared_dir)
        cache_volumes = get_cache_volumes()
        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "--pull",
                        "never",
                        "-d",
                        "--name",
                        "dda-linux-container-default",
                        "-p",
                        "61938:22",
                        "-p",
                        "50069:9000",
                        "-v",
                        "/var/run/docker.sock:/var/run/docker.sock",
                        *host_user_args,
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
                        "-v",
                        f"{shared_dir}:/.shared",
                        *starship_mount,
                        "-v",
                        f"{global_shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        *cache_volumes,
                        "-v",
                        f"{repo_dir}:/root/repos/datadog-agent",
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]

    def test_multiple(self, dda, helpers, mocker, temp_dir, host_user_args):
        repos_dir = temp_dir / "repos"
        repos_dir.ensure_dir()
        repo1_dir = repos_dir / "datadog-agent"
        repo1_dir.ensure_dir()
        repo2_dir = repos_dir / "integrations-core"
        repo2_dir.ensure_dir()

        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        with (
            repo1_dir.as_cwd(),
            helpers.hybrid_patch(
                "subprocess.run",
                return_values={
                    # Start command checks the status
                    1: CompletedProcess([], returncode=0, stdout="{}"),
                    # Start method checks the status
                    2: CompletedProcess([], returncode=0, stdout="{}"),
                    # Capture image pull
                    # Capture container run
                    # Readiness check
                    5: CompletedProcess([], returncode=0, stdout="Server listening on :: port 22"),
                },
            ) as calls,
        ):
            result = dda("env", "dev", "start", "-r", "datadog-agent", "-r", "integrations-core")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Pulling image: datadog/agent-dev-env-linux
                Creating and starting container: dda-linux-container-default
                Waiting for container: dda-linux-container-default
                """
            ),
        )

        assert_ssh_config_written(write_server_config, "localhost")

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / "default" / ".shared"
        global_shared_dir = shared_dir.parent.parent / ".shared"
        starship_mount = get_starship_mount(global_shared_dir)
        cache_volumes = get_cache_volumes()
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "--pull",
                        "never",
                        "-d",
                        "--name",
                        "dda-linux-container-default",
                        "-p",
                        "61938:22",
                        "-p",
                        "50069:9000",
                        "-v",
                        "/var/run/docker.sock:/var/run/docker.sock",
                        *host_user_args,
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
                        "-v",
                        f"{shared_dir}:/.shared",
                        *starship_mount,
                        "-v",
                        f"{global_shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        *cache_volumes,
                        "-v",
                        f"{repo1_dir}:/root/repos/datadog-agent",
                        "-v",
                        f"{repo2_dir}:/root/repos/integrations-core",
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]

    def test_multiple_clones(self, dda, helpers, mocker, temp_dir, host_user_args):
        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # Capture image pull
                # Capture container run
                # Readiness check
                5: CompletedProcess([], returncode=0, stdout="Server listening on :: port 22"),
                # Capture repo cloning
            },
        ) as calls:
            result = dda("env", "dev", "start", "-r", "datadog-agent@tag", "-r", "integrations-core", "--clone")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Pulling image: datadog/agent-dev-env-linux
                Creating and starting container: dda-linux-container-default
                Waiting for container: dda-linux-container-default
                Cloning repository: datadog-agent@tag
                Cloning repository: integrations-core
                """
            ),
        )

        assert_ssh_config_written(write_server_config, "localhost")

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / "default" / ".shared"
        global_shared_dir = shared_dir.parent.parent / ".shared"
        starship_mount = get_starship_mount(global_shared_dir)
        cache_volumes = get_cache_volumes()
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "--pull",
                        "never",
                        "-d",
                        "--name",
                        "dda-linux-container-default",
                        "-p",
                        "61938:22",
                        "-p",
                        "50069:9000",
                        "-v",
                        "/var/run/docker.sock:/var/run/docker.sock",
                        *host_user_args,
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
                        "-v",
                        f"{shared_dir}:/.shared",
                        *starship_mount,
                        "-v",
                        f"{global_shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        *cache_volumes,
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("ssh"),
                        "-A",
                        "-q",
                        "-t",
                        "-p",
                        "61938",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone datadog-agent tag",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE},
            ),
            (
                (
                    [
                        helpers.locate("ssh"),
                        "-A",
                        "-q",
                        "-t",
                        "-p",
                        "61938",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone integrations-core",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE},
            ),
        ]

    @pytest.mark.parametrize(
        ("volume_specs"),
        [
            # Case 1: Single -v
            ["-v", "/tmp/mounted:/tmp/mounted_abs"],
            # Case 2: Single --volume
            ["--volume", "/tmp/mounted:/tmp/mounted_abs"],
            # Case 3: -v and --volume
            ["-v", "/tmp/mounted:/tmp/mounted_abs", "--volume", "./mounted:/tmp/mounted_rel"],
        ],
    )
    def test_extra_volume_specs(self, dda, helpers, mocker, temp_dir, host_user_args, volume_specs):
        mocker.patch("dda.utils.ssh.write_server_config")

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / "default" / ".shared"
        global_shared_dir = shared_dir.parent.parent / ".shared"
        starship_mount = get_starship_mount(global_shared_dir)
        cache_volumes = get_cache_volumes()

        with (
            temp_dir.as_cwd(),
            helpers.hybrid_patch(
                "subprocess.run",
                return_values={
                    # Start command checks the status
                    1: CompletedProcess([], returncode=0, stdout="{}"),
                    # Start method checks the status
                    2: CompletedProcess([], returncode=0, stdout="{}"),
                    # Capture container run
                    # Readiness check
                    4: CompletedProcess([], returncode=0, stdout="Server listening on :: port 22"),
                    # Repo cloning
                    5: CompletedProcess([], returncode=0, stdout="{}"),
                },
            ) as calls,
        ):
            result = dda("env", "dev", "start", "--no-pull", "--clone", *volume_specs)

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Creating and starting container: dda-linux-container-default
                Waiting for container: dda-linux-container-default
                Cloning repository: datadog-agent
                """
            ),
        )
        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "--pull",
                        "never",
                        "-d",
                        "--name",
                        "dda-linux-container-default",
                        "-p",
                        "61938:22",
                        "-p",
                        "50069:9000",
                        "-v",
                        "/var/run/docker.sock:/var/run/docker.sock",
                        *host_user_args,
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
                        "-v",
                        f"{shared_dir}:/.shared",
                        *starship_mount,
                        "-v",
                        f"{global_shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        *cache_volumes,
                        *[(x if x != "-v" else "--volume") for x in volume_specs],
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]

    @pytest.mark.parametrize(
        ("mount_specs"),
        [
            # Case 1: -m, single bind mount
            ["-m", "type=bind,src=/tmp/mounted,dst=/tmp/mounted_abs"],
            # Case 2: -m, single volume mount
            ["-m", "type=volume,src=some-volume,dst=/tmp/mounted_abs"],
            # Case 3: -m, mounts with flags
            [
                "-m",
                "type=bind,source=/tmp/mounted,destination=/tmp/mounted_abs,ro,bind-propagation=rslave",
                "--mount",
                "type=volume,src=some-volume,target=/tmp/mounted_rel,volume-opt=foo=bar,volume-subpath=subpath",
            ],
            # Case 4: -m, --mount, multiple mounts with different syntax
            [
                "-m",
                "type=bind,source=/tmp/mounted,destination=/tmp/mounted_abs",
                "--mount",
                "type=volume,src=some-volume,target=/tmp/mounted_rel",
                "--mount",
                "type=bind,source=./relative,dst=/tmp/mounted_abs,readonly",
            ],
        ],
    )
    def test_extra_mounts(self, dda, helpers, mocker, temp_dir, host_user_args, mount_specs):
        mocker.patch("dda.utils.ssh.write_server_config")

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / "default" / ".shared"
        global_shared_dir = shared_dir.parent.parent / ".shared"
        starship_mount = get_starship_mount(global_shared_dir)
        cache_volumes = get_cache_volumes()

        with (
            temp_dir.as_cwd(),
            helpers.hybrid_patch(
                "subprocess.run",
                return_values={
                    # Start command checks the status
                    1: CompletedProcess([], returncode=0, stdout="{}"),
                    # Start method checks the status
                    2: CompletedProcess([], returncode=0, stdout="{}"),
                    # Capture container run
                    # Readiness check
                    4: CompletedProcess([], returncode=0, stdout="Server listening on :: port 22"),
                    # Repo cloning
                    5: CompletedProcess([], returncode=0, stdout="{}"),
                },
            ) as calls,
        ):
            result = dda("env", "dev", "start", "--no-pull", "--clone", *mount_specs)

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Creating and starting container: dda-linux-container-default
                Waiting for container: dda-linux-container-default
                Cloning repository: datadog-agent
                """
            ),
        )

        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "--pull",
                        "never",
                        "-d",
                        "--name",
                        "dda-linux-container-default",
                        "-p",
                        "61938:22",
                        "-p",
                        "50069:9000",
                        "-v",
                        "/var/run/docker.sock:/var/run/docker.sock",
                        *host_user_args,
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
                        "-v",
                        f"{shared_dir}:/.shared",
                        *starship_mount,
                        "-v",
                        f"{global_shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        *cache_volumes,
                        *[(x if x != "-m" else "--mount") for x in mount_specs],
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]


class TestStop:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "dev", "stop")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot stop developer environment `linux-container` in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # Capture container stop
            },
        ) as calls:
            result = dda("env", "dev", "stop")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Stopping container: dda-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "stop", "-t", "0", "dda-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]


class TestRemove:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "dev", "remove")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot remove developer environment `linux-container` in state `nonexistent`, must be one of: error, stopped
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess(
                    [], returncode=0, stdout=json.dumps([{"State": {"Status": "exited", "ExitCode": 0}}])
                ),
                # Capture container removal
            },
        ) as calls:
            result = dda("env", "dev", "remove")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Removing container: dda-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "rm", "-f", "dda-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]


class TestShell:
    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # Capture ssh command
            },
        ) as calls:
            write_server_config = mocker.patch("dda.utils.ssh.write_server_config")

            result = dda("env", "dev", "shell")

        result.check(exit_code=0)

        assert_ssh_config_written(write_server_config, "localhost")
        assert calls == [
            (
                (
                    [
                        helpers.locate("ssh"),
                        "-A",
                        "-q",
                        "-t",
                        "-p",
                        "61938",
                        "root@localhost",
                        "--",
                        "cd /root/repos/datadog-agent && zsh -l -i",
                    ],
                ),
                {},
            ),
        ]


class TestRun:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "dev", "run", "echo", "foo")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Developer environment `linux-container` is in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        run = mocker.patch("dda.utils.process.SubprocessRunner.run")

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "dev", "run", "echo", "foo")

        result.check(exit_code=0)

        assert_ssh_config_written(write_server_config, "localhost")
        run.assert_called_once_with(
            [
                "ssh",
                "-A",
                "-q",
                "-t",
                "-p",
                "61938",
                "root@localhost",
                "--",
                "cd /root/repos/datadog-agent && echo foo",
            ],
        )


class TestCode:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "dev", "code")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Developer environment `linux-container` is in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        run = mocker.patch("dda.utils.process.SubprocessRunner.run")

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Code command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "dev", "code")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Stopping MCP server
                Starting MCP server
                """
            ),
        )

        assert_ssh_config_written(write_server_config, "localhost")
        run.assert_called_once_with(
            [
                "code",
                "--remote",
                "ssh-remote+root@localhost:61938",
                "/root/repos/datadog-agent",
            ],
        )

    def test_editor_flag(self, dda, helpers, mocker):
        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        run = mocker.patch("dda.utils.process.SubprocessRunner.run")

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Code command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "dev", "code", "--editor", "cursor")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Stopping MCP server
                Starting MCP server
                """
            ),
        )

        assert_ssh_config_written(write_server_config, "localhost")
        run.assert_called_once_with(
            [
                "cursor",
                "--remote",
                "ssh-remote+root@localhost:61938",
                "/root/repos/datadog-agent",
            ],
        )

    def test_editor_config(self, dda, config_file, helpers, mocker):
        config_file.data["env"]["dev"]["editor"] = "cursor"
        config_file.save()

        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        run = mocker.patch("dda.utils.process.SubprocessRunner.run")

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "dev", "code")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Stopping MCP server
                Starting MCP server
                """
            ),
        )

        assert_ssh_config_written(write_server_config, "localhost")
        run.assert_called_once_with(
            [
                "cursor",
                "--remote",
                "ssh-remote+root@localhost:61938",
                "/root/repos/datadog-agent",
            ],
        )


class TestRemoveCache:
    def test_not_stopped(self, dda, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "dev", "cache", "remove")

        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot remove cache for developer environment `linux-container` in state `started`, must be one of: nonexistent, stopped
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                1: CompletedProcess(
                    [], returncode=0, stdout=json.dumps([{"State": {"Status": "exited", "ExitCode": 0}}])
                ),
                2: CompletedProcess([], returncode=0, stdout="foo\ndda-env-dev-linux-container-go_build_cache\nbar"),
                # Capture volume removal
            },
        ) as calls:
            result = dda("env", "dev", "cache", "remove")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Removing cache
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "volume", "rm", "dda-env-dev-linux-container-go_build_cache"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]


class TestCacheSize:
    def test_default(self, dda, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                1: CompletedProcess(
                    [],
                    returncode=0,
                    stdout="""\
foo 1TB
dda-env-dev-linux-container-go_build_cache 512MB
dda-env-dev-linux-container-go_mod_cache 1GB
bar 1PB
""",
                ),
            },
        ):
            result = dda("env", "dev", "cache", "size")

        result.check(
            exit_code=0,
            stdout=helpers.dedent(
                """
                1.50 GiB
                """
            ),
            output=helpers.dedent(
                """
                Calculating cache size
                1.50 GiB
                """
            ),
        )

    def test_empty(self, dda, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                1: CompletedProcess([], returncode=0, stdout="foo 1TB\nbar 1PB"),
            },
        ):
            result = dda("env", "dev", "cache", "size")

        result.check(
            exit_code=0,
            stdout=helpers.dedent(
                """
                Empty
                """
            ),
            output=helpers.dedent(
                """
                Calculating cache size
                Empty
                """
            ),
        )

    def test_bytes(self, dda, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                1: CompletedProcess(
                    [],
                    returncode=0,
                    stdout="""\
foo 1TB
dda-env-dev-linux-container-go_build_cache 1000B
dda-env-dev-linux-container-go_mod_cache 23B
bar 1PB
""",
                ),
            },
        ):
            result = dda("env", "dev", "cache", "size")

        result.check(
            exit_code=0,
            stdout=helpers.dedent(
                """
                1023 B
                """
            ),
            output=helpers.dedent(
                """
                Calculating cache size
                1023 B
                """
            ),
        )


@pytest.fixture
def temp_shared_dir(temp_dir):
    """Temporary shared directory simulating the intermediate location for docker cp."""
    shared = temp_dir / "share_test"
    shared.ensure_dir()
    return shared


@pytest.fixture
def export_destination(temp_dir):
    """Destination directory for exported files."""
    dest = temp_dir / "final_destination"
    dest.ensure_dir()
    return dest


@pytest.fixture
def linux_container_with_shared_dir(app, mocker, temp_shared_dir):
    """LinuxContainer instance configured with a mocked shared temp directory.

    Can be used for both export and import testing.
    """
    container = LinuxContainer(app=app, name="test", instance="default")
    mocker.patch.object(container, "status", return_value=EnvironmentStatus(state=EnvironmentState.STARTED))

    # Mock the temp_directory context manager to return our controlled temp directory
    @contextmanager
    def _temp_directory(dir=None):  # noqa: ARG001, A002
        yield temp_shared_dir

    mocker.patch("dda.utils.fs.temp_directory", _temp_directory)
    return container


class TestExportFiles:
    """Test LinuxContainer.export_files() orchestration of docker cp and import_from_dir."""

    @pytest.mark.parametrize(
        ("sources", "recursive", "force", "mkpath", "expected_docker_cp_calls"),
        [
            pytest.param(
                ("file.txt",),
                False,
                False,
                False,
                [("dda-test-default:file.txt", "file.txt")],
                id="single_file",
            ),
            pytest.param(
                ("file1.txt", "file2.txt"),
                False,
                True,
                False,
                [
                    ("dda-test-default:file1.txt", "file1.txt"),
                    ("dda-test-default:file2.txt", "file2.txt"),
                ],
                id="multiple_files_with_force",
            ),
            pytest.param(
                ("folder",),
                True,
                False,
                False,
                [("dda-test-default:folder", "folder")],
                id="single_directory_recursive",
            ),
            pytest.param(
                ("file.txt", "folder", "file2.txt"),
                True,
                False,
                True,
                [
                    ("dda-test-default:file.txt", "file.txt"),
                    ("dda-test-default:folder", "folder"),
                    ("dda-test-default:file2.txt", "file2.txt"),
                ],
                id="mixed_files_and_directories_with_mkpath",
            ),
            pytest.param(
                ("dir1", "dir2"),
                True,
                True,
                True,
                [
                    ("dda-test-default:dir1", "dir1"),
                    ("dda-test-default:dir2", "dir2"),
                ],
                id="multiple_directories_all_flags",
            ),
        ],
    )
    def test_export_orchestration(
        self,
        mocker,
        linux_container_with_shared_dir,
        temp_shared_dir,
        export_destination,
        sources,
        recursive,
        force,
        mkpath,
        expected_docker_cp_calls,
    ):
        """Verify that export_files correctly orchestrates docker cp and import_from_dir calls."""

        # Track docker cp calls
        docker_cp_calls = []

        def _mock_docker_cp(source: str, destination: str, cwd: Path | None = None) -> None:  # noqa: ARG001
            docker_cp_calls.append((source, destination))

        mocker.patch.object(linux_container_with_shared_dir, "_docker_cp", _mock_docker_cp)

        # Mock import_from_dir where it's used (in linux_container module)
        mock_import_from_dir = mocker.patch("dda.env.dev.types.linux_container.import_from_dir")

        # Execute
        linux_container_with_shared_dir.export_files(
            sources=sources,
            destination=export_destination,
            recursive=recursive,
            force=force,
            mkpath=mkpath,
        )

        # Verify docker cp was called correctly for each source
        assert docker_cp_calls == expected_docker_cp_calls

        # Verify import_from_dir was called once with correct parameters
        mock_import_from_dir.assert_called_once_with(
            temp_shared_dir,
            export_destination,
            recursive=recursive,
            force=force,
            mkpath=mkpath,
        )


class TestImportFiles:
    """Test LinuxContainer.import_files() orchestration of file copying and dda command execution."""

    @pytest.mark.parametrize(
        ("sources", "destination", "recursive", "force", "mkpath"),
        [
            pytest.param(
                ("file_root.txt",),
                "/root/dest",
                False,
                False,
                False,
                id="single_file",
            ),
            pytest.param(
                ("file_root.txt", "file_root2.txt"),
                "/root/dest",
                False,
                True,
                False,
                id="multiple_files_with_force",
            ),
            pytest.param(
                ("folder1",),
                "/root/dest",
                True,
                False,
                False,
                id="single_directory_recursive",
            ),
            pytest.param(
                ("file_root.txt", "folder1", "file_root2.txt"),
                "/root/dest",
                True,
                False,
                True,
                id="mixed_files_and_directories_with_mkpath",
            ),
            pytest.param(
                ("folder1", "folder2"),
                "/root/dest",
                True,
                True,
                True,
                id="multiple_directories_all_flags",
            ),
        ],
    )
    def test_import_orchestration(
        self,
        mocker,
        linux_container_with_shared_dir,
        temp_shared_dir,
        sources,
        destination,
        recursive,
        force,
        mkpath,
    ):
        """Verify that import_files correctly copies files to shared dir and runs dda command."""
        # Get source paths from fixtures
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "fs_tests"
        source_paths = [fixtures_dir / source for source in sources]

        # Mock subprocess.wait to capture the dda command
        mock_subprocess_wait = mocker.patch.object(linux_container_with_shared_dir.app.subprocess, "wait")

        # Execute
        linux_container_with_shared_dir.import_files(
            sources=source_paths,
            destination=destination,
            recursive=recursive,
            force=force,
            mkpath=mkpath,
        )

        # Verify each source was copied to the shared temp directory
        for source in sources:
            shared_path = temp_shared_dir / source
            fixture_path = fixtures_dir / source

            assert shared_path.exists(), f"Expected {source} to be copied to shared directory"

            if fixture_path.is_file():
                # For files, compare content
                assert shared_path.read_text() == fixture_path.read_text()
            else:
                # For directories, verify all contents match recursively
                for fixture_item in fixture_path.rglob("*"):
                    relative_path = fixture_item.relative_to(fixture_path)
                    shared_item = shared_path / relative_path
                    assert shared_item.exists(), f"Missing {relative_path} in copied {source}"
                    if fixture_item.is_file():
                        assert shared_item.read_text() == fixture_item.read_text()

        # Verify the dda command was executed with correct arguments
        mock_subprocess_wait.assert_called_once()
        command = mock_subprocess_wait.call_args[0][0]

        # The command is wrapped in SSH - the last element contains the actual shell command
        shell_command = command[-1].removeprefix("cd /root && ")
        expected = " ".join([
            "dda env dev fs localimport",
            f"/.shared/{temp_shared_dir.name}",
            destination,
            str(recursive),
            str(force),
            str(mkpath),
        ])
        assert expected == shell_command
