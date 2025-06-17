# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field

from dda.env.dev import DEFAULT_DEV_ENV
from dda.utils.editors import AVAILABLE_EDITORS, DEFAULT_EDITOR


class DevEnvConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [env.dev]
    default-type = "linux-container"
    clone-repos = false
    universal-shell = false
    editor = "vscode"
    ```
    ///
    """

    default_type: str = field(name="default-type", default=DEFAULT_DEV_ENV)
    clone_repos: bool = field(name="clone-repos", default=False)
    universal_shell: bool = field(name="universal-shell", default=False)
    editor: str = DEFAULT_EDITOR

    def __post_init__(self) -> None:
        if self.editor not in AVAILABLE_EDITORS:
            message = f"Unknown editor `{self.editor}`, must be one of: {', '.join(AVAILABLE_EDITORS)}"
            raise ValueError(message)


class EnvConfig(Struct, frozen=True):
    dev: DevEnvConfig = field(default_factory=DevEnvConfig)
