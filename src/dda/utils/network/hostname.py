# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cache


@cache
def get_hostname() -> str:
    import socket

    return socket.gethostname().lower()
