# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from enum import IntEnum


class AppEnvVars:
    INTERACTIVE = "DDA_INTERACTIVE"
    QUIET = "DDA_QUIET"
    VERBOSE = "DDA_VERBOSE"
    NO_DYNAMIC_DEPS = "DDA_NO_DYNAMIC_DEPS"
    # https://no-color.org
    NO_COLOR = "NO_COLOR"
    FORCE_COLOR = "FORCE_COLOR"


class ConfigEnvVars:
    DATA = "DDA_DATA_DIR"
    CACHE = "DDA_CACHE_DIR"
    CONFIG = "DDA_CONFIG"


class Verbosity(IntEnum):
    SILENT = -3
    ERROR = -2
    WARNING = -1
    INFO = 0
    VERBOSE = 1
    DEBUG = 2
    TRACE = 3
