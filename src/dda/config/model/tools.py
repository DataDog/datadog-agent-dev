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


class GitConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.git]
    author_details = "inherit"
    ```
    `author_details` can be either:
    - `inherit`: The author name and email will be inherited from the main 'user' config (see [UserConfig](./user.md))
    > The first email will be used if multiple emails are found.
    - `system`: The author name and email will be inherited from the system git config
    ///
    """

    author_details: Literal["inherit", "system"] = "system"


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
