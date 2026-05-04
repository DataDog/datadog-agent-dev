# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import hypothesis
from hypothesis import strategies as st

from dda.utils.network.protocols import derive_service_port


@hypothesis.given(st.text())
def test_derive_service_port(key: str) -> None:
    assert 20000 <= derive_service_port(key) <= 32767
