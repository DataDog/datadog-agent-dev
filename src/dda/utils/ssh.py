# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.utils.fs import Path

RELATIVE_CONFIG_DIR = ".dda"


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


def write_server_config(hostname: str, options: dict[str, str | list[str]]) -> None:
    config_file = ssh_config_dir() / RELATIVE_CONFIG_DIR / hostname
    lines = [f"Host {hostname}"]
    for key, value in options.items():
        if isinstance(value, list):
            lines.extend(f"    {key} {v}" for v in value)
        else:
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
