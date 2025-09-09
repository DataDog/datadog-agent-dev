# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Literal

from msgspec import Struct, field

from dda.utils.git.constants import GitAuthorEnvVars


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


def _get_name_from_git() -> str:
    from os import environ

    from dda.utils.process import static_capture

    if name := environ.get(GitAuthorEnvVars.NAME):
        return name

    return static_capture(["git", "config", "--global", "--get", "user.name"]).strip()


def _get_email_from_git() -> str:
    from os import environ

    from dda.utils.process import static_capture

    if email := environ.get(GitAuthorEnvVars.EMAIL):
        return email

    return static_capture(["git", "config", "--global", "--get", "user.email"]).strip()


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
