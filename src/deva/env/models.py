# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from enum import StrEnum

from msgspec import Struct


class EnvironmentStage(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    STARTING = "starting"
    STOPPING = "stopping"


class EnvironmentStatus(Struct, frozen=True, forbid_unknown_fields=True):
    stage: EnvironmentStage
    info: str = ""
