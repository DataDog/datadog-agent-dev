# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from types import TracebackType


class TelemetryClient(ABC):
    def __init__(
        self,
        *,
        id: str,  # noqa: A002
        api_key: str,
    ) -> None:
        self.__id = id
        self._api_key = api_key

    @property
    def id(self) -> str:
        return self.__id

    @abstractmethod
    def send(self, data: dict[str, Any]) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        pass
