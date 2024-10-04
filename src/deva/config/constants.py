# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from enum import IntEnum


class AppEnvVars:
    INTERACTIVE = "DEVA_INTERACTIVE"
    QUIET = "DEVA_QUIET"
    VERBOSE = "DEVA_VERBOSE"
    # https://no-color.org
    NO_COLOR = "NO_COLOR"
    FORCE_COLOR = "FORCE_COLOR"


class ConfigEnvVars:
    DATA = "DEVA_DATA_DIR"
    CACHE = "DEVA_CACHE_DIR"
    CONFIG = "DEVA_CONFIG"


class Verbosity(IntEnum):
    SILENT = -3
    ERROR = -2
    WARNING = -1
    INFO = 0
    VERBOSE = 1
    DEBUG = 2
    TRACE = 3
