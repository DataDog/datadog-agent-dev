# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def ensure_ssh_config(hostname: str) -> None:
    from dda.utils.ssh import write_server_config

    return write_server_config(
        hostname,
        {
            "StrictHostKeyChecking": "no",
            "ForwardAgent": "yes",
            "UserKnownHostsFile": "/dev/null",
            # Prevent passing local config, only supported on OpenSSH 8.7+ https://www.openssh.com/txt/release-8.7
            "SetEnv": ["TERM=xterm-256color"],
        },
    )
