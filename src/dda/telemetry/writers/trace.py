# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any

from dda.telemetry.writers.base import TelemetryWriter


class TraceTelemetryWriter(TelemetryWriter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(id="trace", **kwargs)

    def span(self, data: dict[str, Any]) -> None:
        """
        Send a trace span to Datadog. Example:

        ```python
        app.telemetry.trace.span({
            "start": time.time_ns(),
            "error": 0,
            "meta": {
                "foo.bar": "baz",
            },
        })
        ```

        The following fields have default values:

        Field | Default value
        --- | ---
        `service` | `dda`
        `trace_id` | A random 64-bit integer.
        `span_id` | A random 64-bit integer.
        `parent_id` | `0`

        Parameters:
            data: The [span](https://docs.datadoghq.com/tracing/guide/send_traces_to_agent_by_api/#model) to send.
        """
        self._write(data)
