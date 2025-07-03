# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.utils.network.protocols import derive_dynamic_port


def test_derive_dynamic_port() -> None:
    assert 49152 <= derive_dynamic_port("key") <= 65535
