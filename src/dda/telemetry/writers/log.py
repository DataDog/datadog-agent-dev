# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any

from dda.telemetry.writers.base import TelemetryWriter


class LogTelemetryWriter(TelemetryWriter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(id="log", **kwargs)

    def write(self, data: dict[str, Any]) -> None:
        """
        Send a log message to Datadog. Example:

        ```python
        app.telemetry.log.write({
            "message": "Hello, world!",
            "level": "info",
            "ddtags": "foo:bar,baz:qux",
        })
        ```

        The following fields have default values:

        Field | Default value
        --- | ---
        `service` | `dda`

        Parameters:
            data: The [log attributes](https://docs.datadoghq.com/logs/log_configuration/attributes_naming_convention/)
                to send.
        """
        self._write(data)
