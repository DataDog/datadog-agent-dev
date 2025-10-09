# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct


class TelemetryConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [telemetry]
    anon = true
    ```
    ///
    """

    anon: bool = True
