# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Literal

from msgspec import Struct, field

from dda.utils.git.constants import GitEnvVars


def _get_name_from_git() -> str:
    from os import environ

    if name := environ.get(GitEnvVars.AUTHOR_NAME):
        return name

    import subprocess

    command = ["git", "config", "--global", "--get", "user.name"]

    try:
        return subprocess.run(
            command,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _get_email_from_git() -> str:
    from os import environ

    if name := environ.get(GitEnvVars.AUTHOR_NAME):
        return name

    import subprocess

    command = ["git", "config", "--global", "--get", "user.email"]

    try:
        return subprocess.run(
            command,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


class BazelConfig(Struct, frozen=True, forbid_unknown_fields=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.bazel]
    managed = "auto"
    ```
    ///
    """

    managed: bool | Literal["auto"] = "auto"


class GitAuthorConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.git.author]
    name = "U.N. Owen"
    email = "void@some.where"
    ```
    ///
    """

    name: str = field(default_factory=_get_name_from_git)
    email: str = field(default_factory=_get_email_from_git)


class GitConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.git]
    ...
    ```
    ///
    """

    author: GitAuthorConfig = field(default_factory=GitAuthorConfig)


class ToolsConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools]
    ...
    ```
    ///
    """

    bazel: BazelConfig = field(default_factory=BazelConfig)
    git: GitConfig = field(default_factory=GitConfig)
