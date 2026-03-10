# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess


SSH_OPTIONS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]


def test_connection(workspace: str) -> bool:
    """Return True if the workspace is reachable via SSH."""
    result = subprocess.run(
        ["ssh", *SSH_OPTIONS, workspace, "echo ok"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "ok"


def run_remote(
    workspace: str,
    command: str,
    *,
    capture_output: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """Run a shell command on the remote workspace and return the result."""
    return subprocess.run(
        ["ssh", *SSH_OPTIONS, workspace, command],
        capture_output=capture_output,
        text=True,
        timeout=timeout,
    )


def stream_remote(workspace: str, command: str) -> subprocess.Popen:
    """
    Start a remote command and return a Popen object for streaming stdout.
    The caller is responsible for reading stdout and waiting for the process.
    """
    return subprocess.Popen(
        ["ssh", *SSH_OPTIONS, workspace, command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
