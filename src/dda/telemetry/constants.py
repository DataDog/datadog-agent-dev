# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda._version import __version__

SERVICE_NAME = "dda"
SERVICE_VERSION = __version__


class DaemonEnvVars:
    COMMAND_PID = "DDA_TELEMETRY_COMMAND_PID"
    WRITE_DIR = "DDA_TELEMETRY_WRITE_DIR"
    LOG_FILE = "DDA_TELEMETRY_LOG_FILE"
