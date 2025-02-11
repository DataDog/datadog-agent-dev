# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct


class TelemetryData(Struct, frozen=True):
    start_time: int
    end_time: int
    command: str
    exit_code: int
