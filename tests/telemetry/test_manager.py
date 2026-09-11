# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import subprocess
import sys

from dda.telemetry.constants import DaemonEnvVars
from dda.telemetry.manager import TelemetryManager


def test_watch_delegates_storage_creation_to_daemon(mocker, temp_dir):
    app = mocker.Mock()
    cache_dir = temp_dir / "cache"
    app.config.storage.cache = cache_dir
    write_dir = temp_dir / "write"
    mocker.patch("tempfile.mkdtemp", return_value=str(write_dir))

    manager = TelemetryManager(app)
    manager.watch()

    storage_dir = cache_dir / "telemetry"
    assert not storage_dir.exists()
    env_vars = app.subprocess.spawn_daemon.call_args.kwargs["env"]
    assert env_vars[DaemonEnvVars.WRITE_DIR] == str(write_dir)
    assert env_vars[DaemonEnvVars.LOG_FILE] == str(storage_dir / "daemon.log")
    assert env_vars[DaemonEnvVars.ERROR_FILE] == str(storage_dir / "daemon.error")


def test_daemon_creates_storage_directory(temp_dir):
    storage_dir = temp_dir / "cache" / "telemetry"
    env_vars = os.environ.copy()
    env_vars[DaemonEnvVars.LOG_FILE] = str(storage_dir / "daemon.log")
    env_vars[DaemonEnvVars.ERROR_FILE] = str(storage_dir / "daemon.error")

    subprocess.run([sys.executable, "-c", "import dda.telemetry.daemon.handler"], env=env_vars, check=True)

    assert storage_dir.is_dir()
