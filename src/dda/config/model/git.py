# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field

from dda.utils._git import get_git_author_email, get_git_author_name


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

    name: str = field(default_factory=get_git_author_name)
    email: str = field(default_factory=get_git_author_email)


class GitConfig(Struct, frozen=True):
    user: GitUser = field(default_factory=GitUser)
