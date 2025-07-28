# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from msgspec import Struct, field


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


class EnvironmentPort(Struct, frozen=True, forbid_unknown_fields=True):
    """
    This class represents a port that an environment exposes.
    """

    port: int
    protocol: str = "tcp"


class EnvironmentPortMetadata(Struct, frozen=True, forbid_unknown_fields=True):
    """
    This class represents ports that an environment exposes.
    """

    # https://docs.datadoghq.com/agent/configuration/network/#inbound
    agent: dict[Literal["apm", "dogstatsd", "expvar", "process_expvar"], EnvironmentPort] = {}
    other: dict[str, EnvironmentPort] = {}


class EnvironmentNetworkMetadata(Struct, frozen=True, forbid_unknown_fields=True):
    """
    This class represents network metadata that may be used to access an environment.
    """

    server: str
    ports: EnvironmentPortMetadata = field(default_factory=EnvironmentPortMetadata)


class EnvironmentMetadata(Struct, frozen=True, forbid_unknown_fields=True):
    """
    This class represents metadata about an environment.
    """

    network: EnvironmentNetworkMetadata
