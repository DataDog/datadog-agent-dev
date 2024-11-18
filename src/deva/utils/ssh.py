# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from deva.utils.fs import Path

RELATIVE_CONFIG_DIR = ".deva"


def ssh_config_dir() -> Path:
    return Path.home() / ".ssh"


def ssh_base_command(destination: str, ssh_port: int | str) -> list[str]:
    return [
        "ssh",
        # Enable agent forwarding
        "-A",
        # Silence redundant output
        "-q",
        # Allocate pseudo-terminal, required for colored output and some commands
        "-t",
        "-p",
        str(ssh_port),
        destination,
        # Indicate that there are no more flags
        "--",
    ]


def derive_dynamic_ssh_port(key: str) -> int:
    from hashlib import sha256

    # https://en.wikipedia.org/wiki/Ephemeral_port
    # https://datatracker.ietf.org/doc/html/rfc6335#section-6
    # https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
    min_port = 49152
    max_port = 65535

    repo_id = int.from_bytes(sha256(key.encode("utf-8")).digest(), "big")
    return repo_id % (max_port - min_port) + min_port


def write_server_config(hostname: str, options: dict[str, str]) -> None:
    config_file = ssh_config_dir() / RELATIVE_CONFIG_DIR / hostname
    lines = [f"Host {hostname}"]
    for key, value in options.items():
        lines.append(f"    {key} {value}")

    lines.append("")
    config_file.parent.ensure_dir()
    config_file.write_text("\n".join(lines), encoding="utf-8")
    ensure_config_inclusion()


def ensure_config_inclusion() -> None:
    config_file = ssh_config_dir() / "config"
    expected_line = f"Include {RELATIVE_CONFIG_DIR}/*"
    lines = config_file.read_text(encoding="utf-8").splitlines() if config_file.exists() else []
    if expected_line in lines:
        return

    new_lines = [expected_line, *lines, ""]
    config_file.parent.ensure_dir()
    config_file.write_text("\n".join(new_lines), encoding="utf-8")
