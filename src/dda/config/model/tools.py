# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Literal

from msgspec import Struct, field

from dda.utils._git import get_git_author_email, get_git_author_name


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


class GitConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.git]
    username = "U.N. Owen"
    user_email = "void@some.where"
    ```
    ///
    """

    # TODO: Do we really want to tie this to git? Should we have a separate section for user info instead?
    # TODO: Do we really want this here ? We are not so much configuring git
    username: str = field(default_factory=get_git_author_name)
    user_email: str = field(default_factory=get_git_author_email)


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
