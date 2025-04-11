# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import subprocess
import sys
from subprocess import CompletedProcess

import msgspec
import pytest

from dda.config.constants import AppEnvVars
from dda.env.dev.types.linux_container import LinuxContainer
from dda.utils.fs import Path

pytestmark = [pytest.mark.usefixtures("private_storage")]


@pytest.fixture(autouse=True)
def updated_config(config_file):
    # Allow Windows users to run these tests
    if sys.platform == "win32":
        config_file.data["env"] = {"dev": {"default-type": "linux-container"}}
        config_file.save()


def get_starship_mount(shared_dir: Path) -> list[str]:
    starship_config_file = Path.home() / ".config" / "starship.toml"
    if not starship_config_file.exists():
        return []

    return ["-v", f"{shared_dir / 'shell' / 'starship.toml'}:/root/.shared/shell/starship.toml"]


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
    }


class TestStatus:
    def test_default(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))
        result = dda("env", "dev", "status")

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            State: nonexistent
            """
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

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            f"""
            State: {state}
            """
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

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Cannot start developer environment `linux-container` in state `started`, must be one of: nonexistent, stopped
            """
        )

    def test_default(self, dda, helpers, mocker, temp_dir):
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

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Pulling image: datadog/agent-dev-env-linux
            Creating and starting container: dda-linux-container-default
            Waiting for container: dda-linux-container-default
            """
        )

        write_server_config.assert_called_once_with(
            "localhost",
            {
                "StrictHostKeyChecking": "no",
                "ForwardAgent": "yes",
                "UserKnownHostsFile": "/dev/null",
            },
        )

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
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
                        "59730:22",
                        "-e",
                        "DD_SHELL",
                        "-e",
                        AppEnvVars.TELEMETRY_API_KEY,
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        "-v",
                        f"{repo_dir}:/root/repos/datadog-agent",
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
            ),
        ]

    def test_clone(self, dda, helpers, mocker, temp_dir):
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

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Pulling image: datadog/agent-dev-env-linux
            Creating and starting container: dda-linux-container-default
            Waiting for container: dda-linux-container-default
            Cloning repository: datadog-agent
            """
        )

        write_server_config.assert_called_once_with(
            "localhost",
            {
                "StrictHostKeyChecking": "no",
                "ForwardAgent": "yes",
                "UserKnownHostsFile": "/dev/null",
            },
        )

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
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
                        "59730:22",
                        "-e",
                        "DD_SHELL",
                        "-e",
                        AppEnvVars.TELEMETRY_API_KEY,
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("ssh"),
                        "-A",
                        "-q",
                        "-t",
                        "-p",
                        "59730",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone datadog-agent",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
            ),
        ]

    def test_no_pull(self, dda, helpers, mocker, temp_dir):
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

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Creating and starting container: dda-linux-container-default
            Waiting for container: dda-linux-container-default
            """
        )

        write_server_config.assert_called_once_with(
            "localhost",
            {
                "StrictHostKeyChecking": "no",
                "ForwardAgent": "yes",
                "UserKnownHostsFile": "/dev/null",
            },
        )

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
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
                        "59730:22",
                        "-e",
                        "DD_SHELL",
                        "-e",
                        AppEnvVars.TELEMETRY_API_KEY,
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        "-v",
                        f"{repo_dir}:/root/repos/datadog-agent",
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
            ),
        ]

    def test_multiple(self, dda, helpers, mocker, temp_dir):
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

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Pulling image: datadog/agent-dev-env-linux
            Creating and starting container: dda-linux-container-default
            Waiting for container: dda-linux-container-default
            """
        )

        write_server_config.assert_called_once_with(
            "localhost",
            {
                "StrictHostKeyChecking": "no",
                "ForwardAgent": "yes",
                "UserKnownHostsFile": "/dev/null",
            },
        )

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
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
                        "59730:22",
                        "-e",
                        "DD_SHELL",
                        "-e",
                        AppEnvVars.TELEMETRY_API_KEY,
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        "-v",
                        f"{repo1_dir}:/root/repos/datadog-agent",
                        "-v",
                        f"{repo2_dir}:/root/repos/integrations-core",
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
            ),
        ]

    def test_multiple_clones(self, dda, helpers, mocker, temp_dir):
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

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Pulling image: datadog/agent-dev-env-linux
            Creating and starting container: dda-linux-container-default
            Waiting for container: dda-linux-container-default
            Cloning repository: datadog-agent@tag
            Cloning repository: integrations-core
            """
        )

        write_server_config.assert_called_once_with(
            "localhost",
            {
                "StrictHostKeyChecking": "no",
                "ForwardAgent": "yes",
                "UserKnownHostsFile": "/dev/null",
            },
        )

        shared_dir = temp_dir / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
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
                        "59730:22",
                        "-e",
                        "DD_SHELL",
                        "-e",
                        AppEnvVars.TELEMETRY_API_KEY,
                        *starship_mount,
                        "-v",
                        f"{shared_dir / 'shell' / 'zsh' / '.zsh_history'}:/root/.shared/shell/zsh/.zsh_history",
                        "datadog/agent-dev-env-linux",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("ssh"),
                        "-A",
                        "-q",
                        "-t",
                        "-p",
                        "59730",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone datadog-agent tag",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
            ),
            (
                (
                    [
                        helpers.locate("ssh"),
                        "-A",
                        "-q",
                        "-t",
                        "-p",
                        "59730",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone integrations-core",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
            ),
        ]


class TestStop:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "dev", "stop")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Cannot stop developer environment `linux-container` in state `nonexistent`, must be `started`
            """
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

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Stopping container: dda-linux-container-default
            """
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "stop", "-t", "0", "dda-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
            ),
        ]


class TestRemove:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "dev", "remove")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Cannot remove developer environment `linux-container` in state `nonexistent`, must be one of: error, stopped
            """
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

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Removing container: dda-linux-container-default
            """
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "rm", "-f", "dda-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": mocker.ANY},
            ),
        ]


class TestShell:
    def test_default(self, dda, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
        )
        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")
        exit_with = mocker.patch("dda.utils.process.SubprocessRunner.exit_with")

        result = dda("env", "dev", "shell")

        assert result.exit_code == 0, result.output
        assert not result.output

        write_server_config.assert_called_once_with(
            "localhost",
            {
                "StrictHostKeyChecking": "no",
                "ForwardAgent": "yes",
                "UserKnownHostsFile": "/dev/null",
            },
        )
        exit_with.assert_called_once_with([
            "ssh",
            "-A",
            "-q",
            "-t",
            "-p",
            "59730",
            "root@localhost",
            "--",
            "cd /root/repos/datadog-agent && zsh -l -i",
        ])


class TestRun:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "dev", "run", "echo", "foo")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Developer environment `linux-container` is in state `nonexistent`, must be `started`
            """
        )

    def test_default(self, dda, helpers, mocker):
        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # Capture command run
            },
        ) as calls:
            result = dda("env", "dev", "run", "echo", "foo")

        assert result.exit_code == 0, result.output
        assert not result.output

        write_server_config.assert_called_once_with(
            "localhost",
            {
                "StrictHostKeyChecking": "no",
                "ForwardAgent": "yes",
                "UserKnownHostsFile": "/dev/null",
            },
        )
        assert calls == [
            (
                (
                    [
                        helpers.locate("ssh"),
                        "-A",
                        "-q",
                        "-t",
                        "-p",
                        "59730",
                        "root@localhost",
                        "--",
                        "cd /root/repos/datadog-agent && echo foo",
                    ],
                ),
                {},
            ),
        ]


class TestCode:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "dev", "code")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Developer environment `linux-container` is in state `nonexistent`, must be `started`
            """
        )

    def test_default(self, dda, helpers, mocker):
        write_server_config = mocker.patch("dda.utils.ssh.write_server_config")

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # Capture VS Code run
            },
        ) as calls:
            result = dda("env", "dev", "code")

        assert result.exit_code == 0, result.output
        assert not result.output

        write_server_config.assert_called_once_with(
            "localhost",
            {
                "StrictHostKeyChecking": "no",
                "ForwardAgent": "yes",
                "UserKnownHostsFile": "/dev/null",
            },
        )
        assert calls == [
            (
                (
                    [
                        helpers.locate("code"),
                        "--remote",
                        "ssh-remote+root@localhost:59730",
                        "/root/repos/datadog-agent",
                    ],
                ),
                {},
            ),
        ]
