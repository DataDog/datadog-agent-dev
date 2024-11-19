# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def wait_for(condition: Callable[[], bool | None], timeout: float = 60, wait: float = 1) -> None:
    start_time = time.monotonic()
    while True:
        try:
            result = condition()
        except Exception:
            elapsed_time = time.monotonic() - start_time
            if elapsed_time >= timeout:
                raise

            time.sleep(wait)
            continue

        if result is not False:
            return

        elapsed_time = time.monotonic() - start_time
        if elapsed_time >= timeout:
            raise TimeoutError

        time.sleep(wait)
