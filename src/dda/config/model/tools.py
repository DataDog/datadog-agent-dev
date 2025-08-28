# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Literal

from msgspec import Struct, field


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

    from dda.tools.git import Git
    from dda.utils.process import static_capture

    if name := environ.get(Git.AUTHOR_NAME_ENV_VAR):
        return name

    return static_capture(["git", "config", "--global", "--get", "user.name"]).strip()


def _get_email_from_git() -> str:
    from os import environ

    from dda.tools.git import Git
    from dda.utils.process import static_capture

    if email := environ.get(Git.AUTHOR_EMAIL_ENV_VAR):
        return email

    return static_capture(["git", "config", "--global", "--get", "user.email"]).strip()


class GitConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.git]
    name = "U.N. Owen"
    email = "void@some.where"
    ```
    ///
    """

    author_name: str = field(default_factory=_get_name_from_git)
    author_email: str = field(default_factory=_get_email_from_git)


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
