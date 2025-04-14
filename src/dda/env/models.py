# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from enum import StrEnum

from msgspec import Struct


class EnvironmentState(StrEnum):
    STARTED = "started"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    NONEXISTENT = "nonexistent"
    UNKNOWN = "unknown"


class EnvironmentStatus(Struct, frozen=True, forbid_unknown_fields=True):
    """
    This class represents the status of an environment.
    """

    state: EnvironmentState
    info: str = ""
