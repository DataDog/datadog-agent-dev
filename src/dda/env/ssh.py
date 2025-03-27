# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def ensure_ssh_config(hostname: str) -> None:
    from dda.utils.ssh import write_server_config

    return write_server_config(
        hostname, {"StrictHostKeyChecking": "no", "ForwardAgent": "yes", "UserKnownHostsFile": "/dev/null"}
    )
