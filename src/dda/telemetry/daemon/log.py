# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Self

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem

from dda.telemetry.constants import SERVICE_NAME
from dda.telemetry.daemon.base import TelemetryClient

if TYPE_CHECKING:
    from types import TracebackType


class LogTelemetryClient(TelemetryClient):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(id="log", **kwargs)

        self.__config = Configuration(api_key={"apiKeyAuth": self._api_key})
        self.__client = ApiClient(self.__config)
        self.__api = LogsApi(self.__client)

    def send(self, data: dict[str, Any]) -> None:
        data.setdefault("service", SERVICE_NAME)

        try:
            log_item = HTTPLogItem(**data)
        except Exception:
            logging.exception("Failed to create HTTPLogItem")
            return

        try:
            self.__api.submit_log(body=HTTPLog(value=[log_item]))
        except Exception:
            logging.exception("Failed to submit log item")
        else:
            logging.info("Submitted log item: %s", data)

    def __enter__(self) -> Self:
        self.__client.__enter__()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self.__client.__exit__(exc_type, exc_value, traceback)
