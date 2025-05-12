# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
import platform
import secrets
import socket
import sys
import time
from functools import cache
from typing import TYPE_CHECKING, Any, Self

from dda.telemetry.constants import SERVICE_NAME, SERVICE_VERSION
from dda.telemetry.daemon.base import TelemetryClient
from dda.utils.network.http.client import get_http_client
from dda.utils.platform import get_machine_id

if TYPE_CHECKING:
    from types import TracebackType

URL = "https://instrumentation-telemetry-intake.datadoghq.com/api/v2/apmtelemetry"

if sys.platform == "win32":

    def get_os_name() -> str:
        return f"{platform.system()} {platform.win32_ver()[0]} {platform.win32_edition()}"

    def get_os_version() -> str:
        return platform.win32_ver()[0]

elif sys.platform == "darwin":

    def get_os_name() -> str:
        return f"{platform.system()} {platform.mac_ver()[0]}"

    def get_os_version() -> str:
        return platform.mac_ver()[0]

else:

    def get_os_name() -> str:
        return platform.freedesktop_os_release()["NAME"]

    def get_os_version() -> str:
        return platform.freedesktop_os_release()["VERSION_ID"]


@cache
def get_base_payload() -> dict[str, Any]:
    return {
        "api_version": "v2",
        "request_type": "traces",
        "runtime_id": str(get_machine_id()),
        "seq_id": 1,
        "debug": False,
        "origin": "agent",
        "host": {
            "hostname": socket.gethostname(),
            "os": get_os_name(),
            "os_version": get_os_version(),
            "architecture": platform.machine(),
            "kernel_name": platform.system(),
            "kernel_release": platform.release(),
            "kernel_version": platform.version(),
        },
        "application": {
            "service_name": SERVICE_NAME,
            "service_version": SERVICE_VERSION,
            "env": "prod",
            "tracer_version": "n/a",
            "language_name": "python",
            "language_version": ".".join(map(str, sys.version_info[:3])),
        },
        "metrics": {
            "_sampling_priority_v1": 2,
        },
    }


class TraceTelemetryClient(TelemetryClient):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(id="trace", **kwargs)

        self.__client = get_http_client()

    def send(self, data: dict[str, Any]) -> None:
        data.setdefault("service", SERVICE_NAME)
        if "trace_id" not in data:
            data["trace_id"] = secrets.randbits(64)
        if "span_id" not in data:
            data["span_id"] = secrets.randbits(64)
        if "parent_id" not in data:
            data["parent_id"] = 0

        payload = {
            "payload": {
                "traces": [[data]],
            },
            "tracer_time": int(time.time()),
        }
        payload.update(get_base_payload())

        try:
            self.__client.post(URL, json=payload, headers={"DD-API-KEY": self._api_key})
        except Exception:
            logging.exception("Failed to submit trace")
        else:
            logging.info("Submitted trace: %s", data)

    def __enter__(self) -> Self:
        self.__client.__enter__()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self.__client.__exit__(exc_type, exc_value, traceback)
