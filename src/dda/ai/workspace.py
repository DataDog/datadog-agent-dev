# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import shlex
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


def start_remote_bg(workspace: str, command: str, remote_log: str) -> None:
    """
    Start a command in the background on the workspace, writing its output to
    remote_log.  Uses `nohup script -q` to allocate a remote PTY (so Node.js
    CLIs stream output) while keeping the process alive after SSH disconnects.

    The PTY column width is set to 32767 before running the command so that
    long stream-json lines are not wrapped in the log file.
    """
    wide_command = f"stty cols 32767 2>/dev/null; {command}"
    bg = f"nohup script -q -c {shlex.quote(wide_command)} {remote_log} > /dev/null 2>&1 &"
    run_remote(workspace, bg)


def stream_remote(workspace: str, command: str) -> subprocess.Popen:
    """
    Start a remote command and return a Popen object for streaming stdout.
    The caller is responsible for reading stdout and waiting for the process.

    Wraps the command in `script -q` to allocate a pseudo-TTY on the *remote*
    side only.  This forces Node.js-based CLIs (like Claude) to stream output
    line-by-line rather than buffering until exit, without touching the local
    terminal or putting it into raw mode.
    """
    import shlex

    wrapped = f"script -q -c {shlex.quote(command)} /dev/null"
    return subprocess.Popen(
        ["ssh", *SSH_OPTIONS, workspace, wrapped],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
