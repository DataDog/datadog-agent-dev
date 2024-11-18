# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from deva.utils.retry import wait_for


class TestWaitFor:
    def test_success(self):
        wait_for(lambda: True, timeout=0)

    def test_unmet(self):
        with pytest.raises(TimeoutError):
            wait_for(lambda: False, timeout=0)

    def test_recover_from_unmet(self):
        counter = 0

        def condition():
            nonlocal counter
            if counter == 0:
                counter += 1
                return False

            return True

        wait_for(condition, wait=0)

    def test_exception(self):
        with pytest.raises(ZeroDivisionError):
            wait_for(lambda: 9 / 0, timeout=0)

    def test_recover_from_exception(self):
        counter = 0

        def condition():
            nonlocal counter
            if counter == 0:
                counter += 1
                raise ValueError

            return True

        wait_for(condition, wait=0)
