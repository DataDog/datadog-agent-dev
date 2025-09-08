# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct


class UserConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [user]
    name = "U.N. Owen"
    email = "void@some.where"
    ```
    These values will be used for dda-related functionality, such as telemetry.
    Both `email` and `name` can be set to `auto`, in which case they will be equal to the values in the [`[tools.git]`][dda.config.model.tools.GitConfig] section.
    ///
    """

    # Default username and email are equal to the values in [tools.git]
    name: str = "auto"
    email: str = "auto"
