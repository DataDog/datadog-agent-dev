# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Literal

from msgspec import Struct, field


class UpdateCheckConfig(Struct, frozen=True, forbid_unknown_fields=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [update.check]
    period = "2w"
    ```
    ///
    """

    period: str = "2w"

    def __post_init__(self) -> None:
        self.get_period_seconds()

    def get_period_seconds(self) -> int:
        import re

        pattern = r"^([0-9]+)([dwm])$"
        if not (match := re.match(pattern, self.period)):
            msg = f"Invalid period, expected format `{pattern}`: {self.period}"
            raise ValueError(msg)

        value, unit = match.groups()
        frequency = int(value)
        if not frequency:
            msg = f"Invalid period, frequency must be a positive integer: {self.period}"
            raise ValueError(msg)

        days = 60 * 60 * 24
        if unit == "d":
            return days * frequency
        if unit == "w":
            return days * 7 * frequency
        if unit == "m":
            return days * 30 * frequency

        msg = f"Invalid period, expected format `{pattern}`: {self.period}"
        raise ValueError(msg)


class UpdateConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [update]
    mode = "check"
    ```
    ///
    """

    mode: Literal["off", "check"] = "check"
    check: UpdateCheckConfig = field(default_factory=UpdateCheckConfig)
