# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.utils.retry import DelayedError, FailFastError, wait_for

ONE_DAY = 24 * 60 * 60


class TestWaitFor:
    def test_success(self):
        wait_for(lambda: None, timeout=0)

    def test_timeout(self):
        with pytest.raises(ZeroDivisionError):
            wait_for(lambda: 9 / 0, timeout=0)

    def test_recovery(self):
        attempts = 0

        def condition():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ValueError

        wait_for(condition, max_delay=0)
        assert attempts == 2

    def test_max_retries(self):
        attempts = 0

        def condition():
            nonlocal attempts
            attempts += 1
            return 9 / 0

        with pytest.raises(ZeroDivisionError):
            wait_for(condition, max_retries=9, max_delay=0)

        assert attempts == 10

    def test_delay_exceeds_timeout(self):
        attempts = 0

        def condition():
            nonlocal attempts
            attempts += 1
            return 9 / 0

        with pytest.raises(ZeroDivisionError):
            wait_for(condition, timeout=0.01, max_retries=1, max_delay=ONE_DAY, min_delay=ONE_DAY)

        assert attempts == 2

    def test_fail_fast(self):
        attempts = 0

        def condition():
            nonlocal attempts
            attempts += 1
            raise FailFastError(ValueError("test"))

        with pytest.raises(ValueError, match="^test$"):
            wait_for(condition)

        assert attempts == 1

    def test_delayed_error_exceeds_timeout(self):
        attempts = 0

        def condition():
            nonlocal attempts
            attempts += 1
            raise DelayedError(ValueError("test"), delay=ONE_DAY)

        with pytest.raises(ValueError, match="^test$"):
            wait_for(condition)

        assert attempts == 1

    def test_delayed_error_recovery(self):
        attempts = 0

        def condition():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise DelayedError(ValueError("test"), delay=0.01)

        wait_for(condition, timeout=ONE_DAY)
        assert attempts == 2
