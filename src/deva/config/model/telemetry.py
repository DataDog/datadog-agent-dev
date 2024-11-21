# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct


class TelemetryConfig(Struct, frozen=True, omit_defaults=True):
    dd_api_key: str = ""
    user_consent: bool = False
