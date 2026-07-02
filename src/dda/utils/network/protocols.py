# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

# Port classes per RFC 6335 §6:
# - System/Well-Known: 0-1023
# - User/Registered: 1024-49151
# - Dynamic/Private/Ephemeral: 49152-65535
#
# We choose a subrange of the User range and keep it:
# - >= 20000 to reduce collisions with commonly used low-numbered ports in practice
# - < 32768 to stay below Linux's default ephemeral start (net.ipv4.ip_local_port_range)
MIN_SERVICE_PORT = 20000
MAX_SERVICE_PORT = 32767
SERVICE_PORT_RANGE = MAX_SERVICE_PORT - MIN_SERVICE_PORT + 1


def derive_service_port(key: str) -> int:
    """
    Deterministically map `key` to a TCP/UDP port.
    """
    from hashlib import sha256

    key_hash = int.from_bytes(sha256(key.encode("utf-8")).digest(), "big")
    return key_hash % SERVICE_PORT_RANGE + MIN_SERVICE_PORT
