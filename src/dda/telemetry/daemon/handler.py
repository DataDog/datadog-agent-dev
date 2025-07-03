# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
import os

from dda.telemetry.constants import DaemonEnvVars
from dda.utils.fs import Path

ERROR_FILE = Path(os.environ[DaemonEnvVars.ERROR_FILE])
ERROR_OCCURRED = False


def set_error() -> None:
    global ERROR_OCCURRED  # noqa: PLW0603
    ERROR_OCCURRED = True


def finalize_error() -> None:
    if ERROR_OCCURRED:
        ERROR_FILE.touch()
    elif ERROR_FILE.is_file():
        ERROR_FILE.unlink()


class ErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: PLR6301
        if record.levelno >= logging.ERROR:
            set_error()
        return True


logging.basicConfig(
    filename=os.environ[DaemonEnvVars.LOG_FILE],
    level=os.environ.get(DaemonEnvVars.LOG_LEVEL, "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logging.getLogger().addFilter(ErrorFilter())
