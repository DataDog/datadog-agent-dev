# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import subprocess
import sys
from subprocess import CompletedProcess

import msgspec
import pytest

from dda.config.constants import AppEnvVars
from dda.env.dev.types.linux_container import LinuxContainer
from dda.utils.container.model import Mount
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


def get_starship_mount(shared_dir: Path) -> list[str]:
    starship_config_file = Path.home() / ".config" / "starship.toml"
    if not starship_config_file.exists():
        return []

    return ["-v", f"{shared_dir / 'shell' / 'starship.toml'}:/root/.shared/shell/starship.toml"]


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

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
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
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
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

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
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
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
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

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
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
                        "GIT_AUTHOR_EMAIL",
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
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

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
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
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
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

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
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
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
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
        ("volume_mount_specs", "result_mounts"),
        [
            # Case 1: -v, Single absolute path
            pytest.param(
                ["-v", "/tmp/mounted:/tmp/mounted_abs"],
                [Mount(type="bind", path="/tmp/mounted_abs", source="/tmp/mounted", read_only=False)],
                id="-v, single_absolute_path",
            ),
            # Case 2: -v, Single relative path
            pytest.param(
                ["-v", "./mounted:/tmp/mounted_rel"],
                [Mount(type="bind", path="/tmp/mounted_rel", source="./mounted", read_only=False)],
                id="-v, single_relative_path",
            ),
            # Case 3: -v, --volume, Multiple mounts
            pytest.param(
                ["-v", "/tmp/mounted:/tmp/mounted_abs", "--volume", "./mounted:/tmp/mounted_rel"],
                [
                    Mount(type="bind", path="/tmp/mounted_abs", source="/tmp/mounted", read_only=False),
                    Mount(type="bind", path="/tmp/mounted_rel", source="./mounted", read_only=False),
                ],
                id="-v, --volume, multiple_mounts",
            ),
            # Case 4: -v, mount with ro flag
            pytest.param(
                ["-v", "/tmp/mounted:/tmp/mounted_abs:ro"],
                [
                    Mount(type="bind", path="/tmp/mounted_abs", source="/tmp/mounted", read_only=True),
                ],
                id="-v, mount_with_ro",
            ),
            # Case 5: -m, single bind mount
            pytest.param(
                ["-m", "type=bind,src=/tmp/mounted,dst=/tmp/mounted_abs"],
                [
                    Mount(type="bind", path="/tmp/mounted_abs", source="/tmp/mounted", read_only=False),
                ],
                id="-m, single_bind_mount",
            ),
            # Case 6: -m, single volume mount
            pytest.param(
                ["-m", "type=volume,src=some-volume,dst=/tmp/mounted_abs"],
                [
                    Mount(type="volume", path="/tmp/mounted_abs", source="some-volume", read_only=False),
                ],
                id="-m, single_volume_mount",
            ),
            # Case 7: -m, mounts with flags
            pytest.param(
                [
                    "-m",
                    "type=bind,source=/tmp/mounted,destination=/tmp/mounted_abs,ro,bind-propagation=rslave",
                    "--mount",
                    "type=volume,src=some-volume,target=/tmp/mounted_rel,volume-opt=foo=bar,volume-subpath=subpath",
                ],
                [
                    Mount(
                        type="bind",
                        path="/tmp/mounted_abs",
                        source="/tmp/mounted",
                        read_only=True,
                        volume_options={"bind-propagation": "rslave"},
                    ),
                    Mount(
                        type="volume",
                        path="/tmp/mounted_rel",
                        source="some-volume",
                        read_only=False,
                        volume_options={"volume-opt": "foo=bar", "volume-subpath": "subpath"},
                    ),
                ],
                id="-m, mounts_with_flags",
            ),
            # Case 8: -m, --mount, multiple mounts with different syntax
            pytest.param(
                [
                    "-m",
                    "type=bind,source=/tmp/mounted,destination=/tmp/mounted_abs",
                    "--mount",
                    "type=volume,src=some-volume,target=/tmp/mounted_rel",
                    "--mount",
                    "type=bind,source=./relative,dst=/tmp/mounted_abs,readonly",
                ],
                [
                    Mount(type="bind", path="/tmp/mounted_abs", source="/tmp/mounted", read_only=False),
                    Mount(type="volume", path="/tmp/mounted_rel", source="some-volume", read_only=False),
                    Mount(type="bind", path="/tmp/mounted_abs", source="./relative", read_only=True),
                ],
                id="-m, --mount, multiple_mounts",
            ),
        ],
    )
    def test_extra_mounts(self, dda, helpers, mocker, temp_dir, host_user_args, volume_mount_specs, result_mounts):
        mocker.patch("dda.utils.ssh.write_server_config")

        # Disable source and destination validation for the extra mount specs
        mocker.patch(
            "dda.env.dev.types.linux_container.__validate_mount_src_dst",
            return_value=None,
        )
        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
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
            result = dda(
                "env",
                "dev",
                "start",
                "--no-pull",
                "--clone",
                *volume_mount_specs,
            )

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
        extra_mounts = []
        for extra_mount in result_mounts:
            extra_mounts.extend(("--mount", extra_mount.as_csv()))

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
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        *cache_volumes,
                        *extra_mounts,
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]

    @pytest.mark.parametrize(
        ("volume_spec", "error_message"),
        [
            pytest.param(
                "/i/dont/exist:/valid/path",
                "Source must be an existing path on the host.",
                id="absolute_src_does_not_exist",
            ),
            pytest.param(
                "./i/dont/exist:/valid/path",
                "Source must be an existing path on the host.",
                id="relative_src_does_not_exist",
            ),
            pytest.param(
                "./:dir",
                "Destination must be an absolute path.",
                id="dst_is_not_absolute",
            ),
            pytest.param(
                "/tmp:/container:foobar",
                "Invalid volume flag: foobar",
                id="invalid_arbitrary_flag",
            ),
            pytest.param(
                "/tmpcontainer",
                "Expected format:",
                id="no_colon",
            ),
        ],
    )
    def test_invalid_volume_specs(self, dda, temp_dir, mocker, volume_spec, error_message):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        with temp_dir.as_cwd():
            result = dda("env", "dev", "start", "-v", volume_spec)

        result.check_exit_code(2)
        assert error_message in result.output

    @pytest.mark.parametrize(
        ("mount_spec", "error_message"),
        [
            # invalid source path (does not exist)
            pytest.param(
                "type=bind,src=/i/dont/exist,dst=/valid/path",
                "Source must be an existing path on the host.",
                id="bind_absolute_src_does_not_exist",
            ),
            pytest.param(
                "type=bind,src=./i/dont/exist,dst=/valid/path",
                "Source must be an existing path on the host.",
                id="bind_relative_src_does_not_exist",
            ),
            # destination path not absolute
            pytest.param(
                "type=bind,src=./,dst=dir",
                "Destination must be an absolute path.",
                id="bind_dst_is_not_absolute",
            ),
            # missing src
            pytest.param(
                "type=bind,dst=/container",
                "Expected format:",
                id="bind_missing_src",
            ),
            # missing dst
            pytest.param(
                "type=bind,src=.",
                "Expected format:",
                id="missing_dst",
            ),
            # src named incorrectly
            pytest.param(
                "type=bind,host=.,dst=/container",
                "Invalid mount source",
                id="src_named_incorrectly",
            ),
            # dst named incorrectly
            pytest.param(
                "type=bind,src=.,container=/container",
                "Invalid mount destination",
                id="dst_named_incorrectly",
            ),
            # type is not supported
            pytest.param(
                "type=foo,ssrc=.,dst=/container",
                "Invalid mount type",
                id="invalid_type",
            ),
            # extra unrelated flag for bind
            pytest.param(
                "type=bind,src=.,dst=/container,foobar=1",
                "Invalid mount flag",
                id="bind_invalid_flag",
            ),
            # extra unrelated flag for volume
            pytest.param(
                "type=volume,src=some-vol,dst=/container,notavolflag=foo",
                "Invalid mount flag",
                id="volume_invalid_flag",
            ),
            # volume flag not supported for bind
            pytest.param(
                "type=bind,src=.,dst=/container,volume-nocopy=1",
                "Invalid mount flag",
                id="bind_invalid_volume_flag",
            ),
        ],
    )
    def test_invalid_mount_specs(self, dda, temp_dir, mocker, mount_spec, error_message):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        with temp_dir.as_cwd():
            result = dda("env", "dev", "start", "-m", mount_spec)

        result.check_exit_code(2)
        assert error_message in result.output


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
