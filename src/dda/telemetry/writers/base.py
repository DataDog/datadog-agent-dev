# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dda.utils.fs import Path


class TelemetryWriter:
    def __init__(
        self,
        *,
        id: str,  # noqa: A002
        path: Path,
        enabled: bool,
    ) -> None:
        self.__id = id
        self.__path = path
        self.__enabled = enabled

    def write(self, data: dict[str, Any]) -> None:
        if not self.__enabled:
            return

        import json
        from uuid import uuid4

        path = self.__path / f"{self.__id}_{uuid4()}.json"
        path.write_atomic(json.dumps(data), "w", encoding="utf-8")
