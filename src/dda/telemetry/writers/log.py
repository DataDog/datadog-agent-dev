# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any

from dda.telemetry.writers.base import TelemetryWriter


class LogTelemetryWriter(TelemetryWriter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(id="log", **kwargs)
