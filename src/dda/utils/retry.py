# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class RetryError(Exception):
    def __init__(self, cause: Exception):
        self.__cause = cause

    @property
    def cause(self) -> Exception:
        return self.__cause

    def __str__(self) -> str:
        return str(self.__cause)


class FailFastError(RetryError):
    """
    An exception indicating that the operation should not be retried.

    Parameters:
        cause: The cause of the failure.
    """


class DelayedError(RetryError):
    """
    An exception indicating that the next attempt should occur after a specific delay.

    Parameters:
        cause: The cause of the failure.
        delay: The delay in seconds.
    """

    def __init__(self, cause: Exception, *, delay: float):
        super().__init__(cause)

        self.__delay = delay

    @property
    def delay(self) -> float:
        return self.__delay


def backoff_delays(
    *,
    max_retries: int | None = None,
    max_delay: float = 30,
    min_delay: float = 1,
    factor: float = 3,
) -> Iterator[float]:
    """
    Generate a sequence of delays using
    [truncated exponential backoff](https://en.wikipedia.org/wiki/Exponential_backoff#Truncated_exponential_backoff)
    with "[decorrelated jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)".

    Parameters:
        max_retries: The maximum number of retries.
        max_delay: The maximum delay.
        min_delay: The minimum delay.
        factor: The growth factor of the delay range.
    """
    import random

    sleep = min_delay
    attempts = 0
    while max_retries is None or attempts < max_retries:
        sleep = min(max_delay, random.uniform(min_delay, sleep * factor))  # noqa: S311
        yield sleep
        attempts += 1


def wait_for(
    condition: Callable[[], Any],
    *,
    timeout: float = 60,
    interval: float | None = None,
    **kwargs: Any,
) -> Any:
    """
    Wait for a condition to be met. The following exceptions influence the retry logic:

    - [`FailFastError`][dda.utils.retry.FailFastError]
    - [`DelayedError`][dda.utils.retry.DelayedError]

    Parameters:
        condition: A callable responsible for checking the condition. A condition is considered satisfied if
            it does not raise an exception.
        timeout: The maximum time to wait for the condition to be met.
        interval: The interval between retries. This is equivalent to setting both `min_delay` and `max_delay` to
            the same value, effectively disabling the exponential backoff.

    Returns:
        The result of the condition.

    Other parameters:
        **kwargs: Additional keyword arguments to pass to [`backoff_delays`][dda.utils.retry.backoff_delays].

    Raises:
        Exception: The final exception is re-raised if a timeout occurs or the maximum number of attempts is reached.
    """
    if interval is not None:
        kwargs["min_delay"] = interval
        kwargs["max_delay"] = interval

    # Do not eagerly iterate through the sequence in order to postpone imports
    delays = backoff_delays(**kwargs)

    start_time = time.monotonic()
    while True:
        try:
            return condition()
        except FailFastError as e:
            raise e.cause from None
        except DelayedError as e:
            if time.monotonic() - start_time + e.delay > timeout:
                raise e.cause from None

            time.sleep(e.delay)
            continue
        except Exception as e:
            elapsed_time = time.monotonic() - start_time
            if elapsed_time >= timeout:
                raise

            try:
                delay = next(delays)
            # Maximum number of attempts reached
            except StopIteration:
                raise e from None

            # Never exceed the timeout
            time.sleep(min(delay, timeout - elapsed_time))
            continue
