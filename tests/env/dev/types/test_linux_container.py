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

from deva.env.dev.types.linux_container import LinuxContainer
from deva.utils.fs import Path

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

    return ["-v", f"{shared_dir / "shell" / "starship.toml"}:/root/.shared/shell/starship.toml"]


def test_default_config(app):
    container = LinuxContainer(app=app, name="linux-container", instance="default")

    assert msgspec.to_builtins(container.config) == {
        "cli": "docker",
        "image": "datadog/agent-dev-env-linux",
        "no_pull": False,
        "repos": ["datadog-agent"],
        "shell": "zsh",
    }


class TestStatus:
    def test_default(self, deva, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))
        result = deva("env", "dev", "status")

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
    def test_states(self, deva, helpers, mocker, state, data):
        mocker.patch(
            "subprocess.run",
            return_value=CompletedProcess([], returncode=0, stdout=json.dumps([{"State": data}])),
        )
        result = deva("env", "dev", "status")

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            f"""
            State: {state}
            """
        )


class TestStart:
    def test_already_started(self, deva, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = deva("env", "dev", "start")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Cannot start developer environment `linux-container` in state `started`, must be one of: nonexistent, stopped
            """
        )

    def test_default(self, deva, helpers, mocker, tmp_path):
        write_server_config = mocker.patch("deva.utils.ssh.write_server_config")
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
            result = deva("env", "dev", "start")

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Pulling image: datadog/agent-dev-env-linux
            Creating and starting container: deva-linux-container-default
            Waiting for container: deva-linux-container-default
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

        shared_dir = tmp_path / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
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
                        "deva-linux-container-default",
                        "-p",
                        "55909:22",
                        "-e",
                        "DD_SHELL=zsh",
                        *starship_mount,
                        "-v",
                        f"{shared_dir / "shell" / "zsh" / ".zsh_history"}:/root/.shared/shell/zsh/.zsh_history",
                        "datadog/agent-dev-env-linux",
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
                        "55909",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone datadog-agent",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
            ),
        ]

    def test_no_pull(self, deva, helpers, mocker, tmp_path):
        write_server_config = mocker.patch("deva.utils.ssh.write_server_config")
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Server listening on :: port 22"),
                # Capture repo cloning
            },
        ) as calls:
            result = deva("env", "dev", "start", "--no-pull")

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Creating and starting container: deva-linux-container-default
            Waiting for container: deva-linux-container-default
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

        shared_dir = tmp_path / "data" / "env" / "dev" / "linux-container" / ".shared"
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
                        "deva-linux-container-default",
                        "-p",
                        "55909:22",
                        "-e",
                        "DD_SHELL=zsh",
                        *starship_mount,
                        "-v",
                        f"{shared_dir / "shell" / "zsh" / ".zsh_history"}:/root/.shared/shell/zsh/.zsh_history",
                        "datadog/agent-dev-env-linux",
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
                        "55909",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone datadog-agent",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
            ),
        ]

    def test_multiple_clones(self, deva, helpers, mocker, tmp_path):
        write_server_config = mocker.patch("deva.utils.ssh.write_server_config")
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
            result = deva("env", "dev", "start", "-r", "datadog-agent@tag", "-r", "integrations-core")

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Pulling image: datadog/agent-dev-env-linux
            Creating and starting container: deva-linux-container-default
            Waiting for container: deva-linux-container-default
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

        shared_dir = tmp_path / "data" / "env" / "dev" / "linux-container" / ".shared"
        starship_mount = get_starship_mount(shared_dir)
        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent-dev-env-linux"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
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
                        "deva-linux-container-default",
                        "-p",
                        "55909:22",
                        "-e",
                        "DD_SHELL=zsh",
                        *starship_mount,
                        "-v",
                        f"{shared_dir / "shell" / "zsh" / ".zsh_history"}:/root/.shared/shell/zsh/.zsh_history",
                        "datadog/agent-dev-env-linux",
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
                        "55909",
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
                        "55909",
                        "root@localhost",
                        "--",
                        "cd /root && git dd-clone integrations-core",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
            ),
        ]


class TestStop:
    def test_nonexistent(self, deva, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = deva("env", "dev", "stop")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Cannot stop developer environment `linux-container` in state `nonexistent`, must be `started`
            """
        )

    def test_default(self, deva, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # Capture container stop
            },
        ) as calls:
            result = deva("env", "dev", "stop")

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Stopping container: deva-linux-container-default
            """
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "stop", "-t", "0", "deva-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
            ),
        ]


class TestRemove:
    def test_nonexistent(self, deva, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = deva("env", "dev", "remove")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Cannot remove developer environment `linux-container` in state `nonexistent`, must be one of: error, stopped
            """
        )

    def test_default(self, deva, helpers):
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
            result = deva("env", "dev", "remove")

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            Removing container: deva-linux-container-default
            """
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "rm", "-f", "deva-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT},
            ),
        ]


class TestShell:
    def test_default(self, deva, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
        )
        write_server_config = mocker.patch("deva.utils.ssh.write_server_config")
        exit_with_command = mocker.patch("deva.utils.process.SubprocessRunner.replace_current_process")

        result = deva("env", "dev", "shell")

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
        exit_with_command.assert_called_once_with([
            "ssh",
            "-A",
            "-q",
            "-t",
            "-p",
            "55909",
            "root@localhost",
            "--",
            "cd /root/repos/datadog-agent && zsh -l -i",
        ])


class TestRun:
    def test_nonexistent(self, deva, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = deva("env", "dev", "run", "echo", "foo")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Developer environment `linux-container` is in state `nonexistent`, must be `started`
            """
        )

    def test_default(self, deva, helpers, mocker):
        write_server_config = mocker.patch("deva.utils.ssh.write_server_config")

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # Capture command run
            },
        ) as calls:
            result = deva("env", "dev", "run", "echo", "foo")

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
                        "55909",
                        "root@localhost",
                        "--",
                        "cd /root/repos/datadog-agent && echo foo",
                    ],
                ),
                {},
            ),
        ]


class TestCode:
    def test_nonexistent(self, deva, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = deva("env", "dev", "code")

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Developer environment `linux-container` is in state `nonexistent`, must be `started`
            """
        )

    def test_default(self, deva, helpers, mocker):
        write_server_config = mocker.patch("deva.utils.ssh.write_server_config")

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # Capture VS Code run
            },
        ) as calls:
            result = deva("env", "dev", "code")

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
                        "ssh-remote+root@localhost:55909",
                        "/root/repos/datadog-agent",
                    ],
                ),
                {},
            ),
        ]
