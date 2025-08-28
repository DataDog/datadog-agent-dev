# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import partial

from msgspec import Struct, field

from dda.tools.git import Git


class UserConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [user]
    name = "U.N. Owen"
    email = ""void@some.where"
    ```
    ///
    """

    # Default username and email are fetched from git config
    name: str = field(default_factory=partial(Git._query_author_name, check=False))  # noqa: SLF001
    email: str = field(default_factory=partial(Git._query_author_email, check=False))  # noqa: SLF001
