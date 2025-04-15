# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def wait_for(condition: Callable[[], bool | None], *, timeout: float = 60, wait: float = 1) -> None:
    """
    Wait for a condition to be met.

    Args:
        condition: A callable responsible for checking the condition. A condition is considered unsatisfied if
            it returns `False` or raises an exception.
        timeout: The maximum time to wait for the condition to be met.
        wait: The time to wait between each check.

    Raises:
        TimeoutError: If a timeout occurs and the final check returned `False`.
        Exception: If a timeout occurs and the final check raised an exception. In this case, the exception is
            re-raised.
    """
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
            message = f"Condition not met after {timeout} seconds"
            raise TimeoutError(message)

        time.sleep(wait)
