# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def derive_dynamic_port(key: str) -> int:
    from hashlib import sha256

    # https://en.wikipedia.org/wiki/Ephemeral_port
    # https://datatracker.ietf.org/doc/html/rfc6335#section-6
    # https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
    min_port = 49152
    max_port = 65535

    repo_id = int.from_bytes(sha256(key.encode("utf-8")).digest(), "big")
    return repo_id % (max_port - min_port) + min_port
