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

    These values will be used for `dda`-related functionality like telemetry. Both `email` and `name` can be
    set to `auto`, in which case they will be equal to the values in the
    [`[tools.git.author]`][dda.config.model.tools.GitAuthorConfig] section.
    ///
    """

    name: str = "auto"
    email: str = "auto"
