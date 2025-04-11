# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field


def _get_config(env_var: str, config_name: str) -> str:
    import os

    value = os.environ.get(env_var, "")
    if value:
        return value

    import subprocess

    try:
        return subprocess.run(
            ["git", "config", "--global", "--get", config_name],  # noqa: S607
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def default_user_name() -> str:
    return _get_config("GIT_AUTHOR_NAME", "user.name")


def default_user_email() -> str:
    return _get_config("GIT_AUTHOR_EMAIL", "user.email")


class GitUser(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [git.user]
    name = "U.N. Owen"
    email = "void@some.where"
    ```
    ///
    """

    name: str = field(default_factory=default_user_name)
    email: str = field(default_factory=default_user_email)


class GitConfig(Struct, frozen=True):
    user: GitUser = field(default_factory=GitUser)
