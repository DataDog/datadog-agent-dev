# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import subprocess
import sys
from subprocess import CompletedProcess

import msgspec
import pytest

from dda.env.qa.types.linux_container import LinuxContainer
from dda.utils.container.model import Mount
from dda.utils.process import PLATFORM_ID

pytestmark = [pytest.mark.usefixtures("private_storage")]


@pytest.fixture(autouse=True)
def _updated_config(config_file):
    # Allow Windows users to run these tests
    if sys.platform == "win32":
        config_file.data["env"] = {"qa": {"default-type": "linux-container"}}
        config_file.save()


@pytest.fixture(scope="module")
def default_network_args():
    def _default_network_args(args):
        return ["--network", "host"] if PLATFORM_ID == "linux" else args

    return _default_network_args


def test_default_config(app):
    container = LinuxContainer(app=app, name="linux-container", instance="default")

    assert msgspec.to_builtins(container.config) == {
        "arch": None,
        "cli": "docker",
        "env": {},
        "e2e": False,
        "image": "datadog/agent",
        "network": "",
        "pull": False,
    }


class TestStatus:
    def test_default(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))
        result = dda("env", "qa", "status")
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
        result = dda("env", "qa", "status")
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
            result = dda("env", "qa", "start")

        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot start QA environment `default` of type `linux-container` in state `started`, must be one of: nonexistent, stopped
                """
            ),
        )

    def test_stopped(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess(
                    [],
                    returncode=0,
                    stdout=json.dumps([{"State": {"Status": "exited", "ExitCode": 0}}]),
                ),
            },
        ) as calls:
            result = dda("env", "qa", "start")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Starting container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "start",
                        "dda-qa-linux-container-default",
                    ],
                ),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]

    def test_default(self, dda, helpers, hostname, default_network_args):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # 3: Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ) as calls:
            result = dda("env", "qa", "start")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                No API key set in the Agent config, using a placeholder
                Creating and starting container: dda-qa-linux-container-default
                Waiting for container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "-d",
                        "--name",
                        "dda-qa-linux-container-default",
                        "--mount",
                        "type=bind,src=/proc,dst=/host/proc",
                        "-e",
                        "DD_API_KEY",
                        "-e",
                        "DD_CMD_PORT",
                        "-e",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC",
                        "-e",
                        "DD_DOGSTATSD_PORT",
                        "-e",
                        "DD_HOSTNAME",
                        *default_network_args([
                            "-p",
                            "57680:57680",
                            "-p",
                            "65351:65351/udp",
                        ]),
                        "datadog/agent",
                    ],
                ),
                {
                    "encoding": "utf-8",
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "env": helpers.ExpectedEnvVars({
                        "DD_API_KEY": "a" * 32,
                        "DD_CMD_PORT": "57680",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC": "true",
                        "DD_DOGSTATSD_PORT": "65351",
                        "DD_HOSTNAME": hostname,
                    }),
                },
            ),
        ]

    def test_api_key_configured(self, dda, helpers, config_file, hostname, default_network_args):
        api_key = "test" * 8
        config_file.data["orgs"]["default"]["api_key"] = api_key
        config_file.save()

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ) as calls:
            result = dda("env", "qa", "start")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Creating and starting container: dda-qa-linux-container-default
                Waiting for container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "-d",
                        "--name",
                        "dda-qa-linux-container-default",
                        "--mount",
                        "type=bind,src=/proc,dst=/host/proc",
                        "-e",
                        "DD_API_KEY",
                        "-e",
                        "DD_CMD_PORT",
                        "-e",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC",
                        "-e",
                        "DD_DOGSTATSD_PORT",
                        "-e",
                        "DD_HOSTNAME",
                        *default_network_args([
                            "-p",
                            "57680:57680",
                            "-p",
                            "65351:65351/udp",
                        ]),
                        "datadog/agent",
                    ],
                ),
                {
                    "encoding": "utf-8",
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "env": helpers.ExpectedEnvVars({
                        "DD_API_KEY": api_key,
                        "DD_CMD_PORT": "57680",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC": "true",
                        "DD_DOGSTATSD_PORT": "65351",
                        "DD_HOSTNAME": hostname,
                    }),
                },
            ),
        ]

    def test_pull(self, dda, helpers, hostname, default_network_args, mocker):
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
                5: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ) as calls:
            result = dda("env", "qa", "start", "--pull")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Pulling image: datadog/agent
                No API key set in the Agent config, using a placeholder
                Creating and starting container: dda-qa-linux-container-default
                Waiting for container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "-d",
                        "--name",
                        "dda-qa-linux-container-default",
                        "--mount",
                        "type=bind,src=/proc,dst=/host/proc",
                        "-e",
                        "DD_API_KEY",
                        "-e",
                        "DD_CMD_PORT",
                        "-e",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC",
                        "-e",
                        "DD_DOGSTATSD_PORT",
                        "-e",
                        "DD_HOSTNAME",
                        *default_network_args([
                            "-p",
                            "57680:57680",
                            "-p",
                            "65351:65351/udp",
                        ]),
                        "datadog/agent",
                    ],
                ),
                {
                    "encoding": "utf-8",
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "env": helpers.ExpectedEnvVars({
                        "DD_API_KEY": "a" * 32,
                        "DD_CMD_PORT": "57680",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC": "true",
                        "DD_DOGSTATSD_PORT": "65351",
                        "DD_HOSTNAME": hostname,
                    }),
                },
            ),
        ]

    def test_arch(self, dda, helpers, hostname, default_network_args, mocker):
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
                5: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ) as calls:
            result = dda("env", "qa", "start", "--pull", "--arch", "arm64")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Pulling image: datadog/agent
                No API key set in the Agent config, using a placeholder
                Creating and starting container: dda-qa-linux-container-default
                Waiting for container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "pull", "datadog/agent", "--platform", "linux/arm64"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "-d",
                        "--name",
                        "dda-qa-linux-container-default",
                        "--platform",
                        "linux/arm64",
                        "--mount",
                        "type=bind,src=/proc,dst=/host/proc",
                        "-e",
                        "DD_API_KEY",
                        "-e",
                        "DD_CMD_PORT",
                        "-e",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC",
                        "-e",
                        "DD_DOGSTATSD_PORT",
                        "-e",
                        "DD_HOSTNAME",
                        *default_network_args([
                            "-p",
                            "57680:57680",
                            "-p",
                            "65351:65351/udp",
                        ]),
                        "datadog/agent",
                    ],
                ),
                {
                    "encoding": "utf-8",
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "env": helpers.ExpectedEnvVars({
                        "DD_API_KEY": "a" * 32,
                        "DD_CMD_PORT": "57680",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC": "true",
                        "DD_DOGSTATSD_PORT": "65351",
                        "DD_HOSTNAME": hostname,
                    }),
                },
            ),
        ]

    def test_network(self, dda, helpers, hostname):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # 3: Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ) as calls:
            result = dda("env", "qa", "start", "--network", "foo")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                No API key set in the Agent config, using a placeholder
                Creating and starting container: dda-qa-linux-container-default
                Waiting for container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "-d",
                        "--name",
                        "dda-qa-linux-container-default",
                        "--mount",
                        "type=bind,src=/proc,dst=/host/proc",
                        "-e",
                        "DD_API_KEY",
                        "-e",
                        "DD_CMD_PORT",
                        "-e",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC",
                        "-e",
                        "DD_DOGSTATSD_PORT",
                        "-e",
                        "DD_HOSTNAME",
                        "--network",
                        "foo",
                        "datadog/agent",
                    ],
                ),
                {
                    "encoding": "utf-8",
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "env": helpers.ExpectedEnvVars({
                        "DD_API_KEY": "a" * 32,
                        "DD_CMD_PORT": "57680",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC": "true",
                        "DD_DOGSTATSD_PORT": "65351",
                        "DD_HOSTNAME": hostname,
                    }),
                },
            ),
        ]

    def test_extra_env_vars(self, dda, helpers, hostname, default_network_args):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # 3: Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ) as calls:
            result = dda("env", "qa", "start", "--env", "EXTRA1", "foo", "--env", "EXTRA2", "bar")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                No API key set in the Agent config, using a placeholder
                Creating and starting container: dda-qa-linux-container-default
                Waiting for container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "-d",
                        "--name",
                        "dda-qa-linux-container-default",
                        "--mount",
                        "type=bind,src=/proc,dst=/host/proc",
                        "-e",
                        "DD_API_KEY",
                        "-e",
                        "DD_CMD_PORT",
                        "-e",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC",
                        "-e",
                        "DD_DOGSTATSD_PORT",
                        "-e",
                        "DD_HOSTNAME",
                        "-e",
                        "EXTRA1",
                        "-e",
                        "EXTRA2",
                        *default_network_args([
                            "-p",
                            "57680:57680",
                            "-p",
                            "65351:65351/udp",
                        ]),
                        "datadog/agent",
                    ],
                ),
                {
                    "encoding": "utf-8",
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "env": helpers.ExpectedEnvVars({
                        "DD_API_KEY": "a" * 32,
                        "DD_CMD_PORT": "57680",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC": "true",
                        "DD_DOGSTATSD_PORT": "65351",
                        "DD_HOSTNAME": hostname,
                        "EXTRA1": "foo",
                        "EXTRA2": "bar",
                    }),
                },
            ),
        ]

    def test_config_template(self, dda, helpers, hostname, temp_dir, default_network_args):
        template_dir = temp_dir / "data" / "env" / "config" / "templates" / "default"
        template_dir.ensure_dir()
        (template_dir / "datadog.yaml").write_text(
            helpers.dedent(
                """
                api_key: foo
                app_key: bar
                use_dogstatsd: false
                apm_config:
                  enabled: true
                process_config:
                  process_collection:
                    enabled: true
                expvar_port: 8126
                """
            )
        )
        integrations_dir = template_dir / "integrations"
        integrations_dir.ensure_dir()

        config_dir = temp_dir / "data" / "env" / "qa" / "linux-container" / "default" / ".state" / "agent_config"
        integration_mount_args = []
        for integration in ["bar", "foo"]:
            integration_dir = integrations_dir / integration
            integration_dir.ensure_dir()
            (integration_dir / "config.yaml").write_text(
                helpers.dedent(
                    """
                    instances:
                    - name: foo
                    """
                )
            )
            mount = Mount(
                type="bind",
                path=f"/etc/datadog-agent/conf.d/{integration}.d",
                source=str(config_dir / "integrations" / integration),
            )
            integration_mount_args.extend(("--mount", mount.as_csv()))

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # 3: Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ) as calls:
            result = dda("env", "qa", "start")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Creating and starting container: dda-qa-linux-container-default
                Waiting for container: dda-qa-linux-container-default
                """
            ),
        )

        state_dir = temp_dir / "data" / "env" / "qa" / "linux-container" / "default" / ".state"
        assert state_dir.is_dir()
        assert (state_dir / "agent_config" / "datadog.yaml").exists()
        assert (state_dir / "agent_config" / "integrations" / "foo" / "config.yaml").exists()
        assert (state_dir / "agent_config" / "integrations" / "bar" / "config.yaml").exists()

        assert calls == [
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "-d",
                        "--name",
                        "dda-qa-linux-container-default",
                        "--mount",
                        "type=bind,src=/proc,dst=/host/proc",
                        *integration_mount_args,
                        "-e",
                        "DD_API_KEY",
                        "-e",
                        "DD_APM_CONFIG_ENABLED",
                        "-e",
                        "DD_APP_KEY",
                        "-e",
                        "DD_CMD_PORT",
                        "-e",
                        "DD_EXPVAR_PORT",
                        "-e",
                        "DD_HOSTNAME",
                        "-e",
                        "DD_PROCESS_CONFIG_EXPVAR_PORT",
                        "-e",
                        "DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED",
                        "-e",
                        "DD_RECEIVER_PORT",
                        "-e",
                        "DD_USE_DOGSTATSD",
                        *default_network_args([
                            "-p",
                            "57680:57680",
                            "-p",
                            "61712:61712/tcp",
                            "-p",
                            "52892:52892/tcp",
                            "-p",
                            "60495:60495/tcp",
                        ]),
                        "datadog/agent",
                    ],
                ),
                {
                    "encoding": "utf-8",
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "env": helpers.ExpectedEnvVars({
                        "DD_API_KEY": "foo",
                        "DD_APM_CONFIG_ENABLED": "true",
                        "DD_APP_KEY": "bar",
                        "DD_CMD_PORT": "57680",
                        "DD_EXPVAR_PORT": "60495",
                        "DD_HOSTNAME": hostname,
                        "DD_PROCESS_CONFIG_EXPVAR_PORT": "52892",
                        "DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED": "true",
                        "DD_RECEIVER_PORT": "61712",
                        "DD_USE_DOGSTATSD": "false",
                    }),
                },
            ),
        ]


class TestStop:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "qa", "stop")

        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot stop QA environment `default` of type `linux-container` in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Stop command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # 2: Capture container stop
            },
        ) as calls:
            result = dda("env", "qa", "stop")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Stopping container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "stop", "dda-qa-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]


class TestRestart:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "qa", "restart")

        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot restart QA environment `default` of type `linux-container` in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Restart command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # 2: Capture container restart
            },
        ) as calls:
            result = dda("env", "qa", "restart")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Restarting container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "restart", "dda-qa-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]


class TestRemove:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "qa", "remove")

        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot remove QA environment `default` of type `linux-container` in state `nonexistent`, must be one of: error, stopped
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Remove command checks the status
                1: CompletedProcess(
                    [], returncode=0, stdout=json.dumps([{"State": {"Status": "exited", "ExitCode": 0}}])
                ),
                # 2: Capture container removal
            },
        ) as calls:
            result = dda("env", "qa", "remove")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Removing container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "rm", "-f", "dda-qa-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
        ]


class TestRun:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "qa", "run", "echo", "foo")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                QA environment `default` of type `linux-container` is in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Run command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # 2: Capture container exec
            },
        ) as calls:
            result = dda("--interactive", "env", "qa", "run", "echo", "foo")

        result.check_exit_code(0)

        assert calls == [
            (
                ([helpers.locate("docker"), "exec", "-t", "dda-qa-linux-container-default", "echo", "foo"],),
                {"cwd": None, "env": mocker.ANY},
            ),
        ]


class TestSyncAgentConfig:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "qa", "config", "sync")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot sync Agent configuration for QA environment `default` of type `linux-container` in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_default(self, dda, helpers, hostname, default_network_args, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # 3: Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ):
            result = dda("env", "qa", "start")
            result.check_exit_code(0)

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Sync command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # 2: Capture container stop
                # 3: Capture container remove
                # 4: Capture container start
                # Readiness check
                5: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ) as calls:
            result = dda("env", "qa", "config", "sync")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                Stopping container: dda-qa-linux-container-default
                Removing container: dda-qa-linux-container-default
                No API key set in the Agent config, using a placeholder
                Creating and starting container: dda-qa-linux-container-default
                Waiting for container: dda-qa-linux-container-default
                """
            ),
        )

        assert calls == [
            (
                ([helpers.locate("docker"), "stop", "dda-qa-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                ([helpers.locate("docker"), "rm", "-f", "dda-qa-linux-container-default"],),
                {"encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "env": mocker.ANY},
            ),
            (
                (
                    [
                        helpers.locate("docker"),
                        "run",
                        "-d",
                        "--name",
                        "dda-qa-linux-container-default",
                        "--mount",
                        "type=bind,src=/proc,dst=/host/proc",
                        "-e",
                        "DD_API_KEY",
                        "-e",
                        "DD_CMD_PORT",
                        "-e",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC",
                        "-e",
                        "DD_DOGSTATSD_PORT",
                        "-e",
                        "DD_HOSTNAME",
                        *default_network_args([
                            "-p",
                            "57680:57680",
                            "-p",
                            "65351:65351/udp",
                        ]),
                        "datadog/agent",
                    ],
                ),
                {
                    "encoding": "utf-8",
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "env": helpers.ExpectedEnvVars({
                        "DD_API_KEY": "a" * 32,
                        "DD_CMD_PORT": "57680",
                        "DD_DOGSTATSD_NON_LOCAL_TRAFFIC": "true",
                        "DD_DOGSTATSD_PORT": "65351",
                        "DD_HOSTNAME": hostname,
                    }),
                },
            ),
        ]


class TestInfo:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "qa", "info")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                QA environment `default` of type `linux-container` does not exist
                """
            ),
        )

    def test_default(self, dda, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # 3: Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ):
            result = dda("env", "qa", "start")

        result.check_exit_code(0)

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Info command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "qa", "info")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                ┌─────────┬───────────────────────────────────────────────────────────────┐
                │ network │ ┌────────┬──────────────────────────────────────────────────┐ │
                │         │ │ server │ localhost                                        │ │
                │         │ │ ports  │ ┌───────┬──────────────────────────────────────┐ │ │
                │         │ │        │ │ agent │ ┌───────────┬──────────────────────┐ │ │ │
                │         │ │        │ │       │ │ dogstatsd │ ┌──────────┬───────┐ │ │ │ │
                │         │ │        │ │       │ │           │ │ port     │ 65351 │ │ │ │ │
                │         │ │        │ │       │ │           │ │ protocol │ udp   │ │ │ │ │
                │         │ │        │ │       │ │           │ └──────────┴───────┘ │ │ │ │
                │         │ │        │ │       │ └───────────┴──────────────────────┘ │ │ │
                │         │ │        │ │ other │ {}                                   │ │ │
                │         │ │        │ └───────┴──────────────────────────────────────┘ │ │
                │         │ └────────┴──────────────────────────────────────────────────┘ │
                └─────────┴───────────────────────────────────────────────────────────────┘
                """
            ),
        )

    def test_status(self, dda, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # 3: Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ):
            result = dda("env", "qa", "start")
            result.check_exit_code(0)

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Info command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "qa", "info", "--status")

        result.check(
            exit_code=0,
            output=helpers.dedent(
                """
                ┌─────────┬───────────────────────────────────────────────────────────────┐
                │ network │ ┌────────┬──────────────────────────────────────────────────┐ │
                │         │ │ server │ localhost                                        │ │
                │         │ │ ports  │ ┌───────┬──────────────────────────────────────┐ │ │
                │         │ │        │ │ agent │ ┌───────────┬──────────────────────┐ │ │ │
                │         │ │        │ │       │ │ dogstatsd │ ┌──────────┬───────┐ │ │ │ │
                │         │ │        │ │       │ │           │ │ port     │ 65351 │ │ │ │ │
                │         │ │        │ │       │ │           │ │ protocol │ udp   │ │ │ │ │
                │         │ │        │ │       │ │           │ └──────────┴───────┘ │ │ │ │
                │         │ │        │ │       │ └───────────┴──────────────────────┘ │ │ │
                │         │ │        │ │ other │ {}                                   │ │ │
                │         │ │        │ └───────┴──────────────────────────────────────┘ │ │
                │         │ └────────┴──────────────────────────────────────────────────┘ │
                │ status  │ ┌───────┬─────────┐                                           │
                │         │ │ state │ started │                                           │
                │         │ │ info  │         │                                           │
                │         │ └───────┴─────────┘                                           │
                └─────────┴───────────────────────────────────────────────────────────────┘
                """
            ),
        )

    def test_json(self, dda, helpers):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Start command checks the status
                1: CompletedProcess([], returncode=0, stdout="{}"),
                # Start method checks the status
                2: CompletedProcess([], returncode=0, stdout="{}"),
                # 3: Capture container run
                # Readiness check
                4: CompletedProcess([], returncode=0, stdout="Starting Datadog Agent v9000"),
            },
        ):
            result = dda("env", "qa", "start")
            result.check_exit_code(0)

        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Info command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            },
        ):
            result = dda("env", "qa", "info", "--status", "--json")

        result.check(
            exit_code=0,
            stdout_json={
                "network": {
                    "server": "localhost",
                    "ports": {
                        "agent": {
                            "dogstatsd": {"port": 65351, "protocol": "udp"},
                        },
                        "other": {},
                    },
                },
                "status": {
                    "state": "started",
                    "info": "",
                },
            },
        )


class TestShell:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "qa", "shell")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot spawn shell in QA environment `default` of type `linux-container` in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_default(self, dda, helpers, mocker):
        with helpers.hybrid_patch(
            "subprocess.run",
            return_values={
                # Shell command checks the status
                1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
                # 2: Capture container exec
            },
        ) as calls:
            result = dda("env", "qa", "shell")

        result.check_exit_code(0)

        assert calls == [
            (
                ([helpers.locate("docker"), "exec", "-it", "dda-qa-linux-container-default", "bash"],),
                {"env": mocker.ANY},
            ),
        ]


class TestGUI:
    def test_nonexistent(self, dda, helpers, mocker):
        mocker.patch("subprocess.run", return_value=CompletedProcess([], returncode=0, stdout="{}"))

        result = dda("env", "qa", "gui")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                Cannot stop QA environment `default` of type `linux-container` in state `nonexistent`, must be `started`
                """
            ),
        )

    def test_not_supported(self, dda, helpers, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
        )

        result = dda("env", "qa", "gui")
        result.check(
            exit_code=1,
            output=helpers.dedent(
                """
                QA environment type does not support GUI access: linux-container
                """
            ),
        )
