# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field


def _get_name() -> str:
    from os import environ

    from dda.tools.git import Git
    from dda.utils.process import SubprocessRunner

    if name := environ.get(Git.AUTHOR_NAME_ENV_VAR):
        return name

    return SubprocessRunner.static_capture(["git", "config", "--global", "--get", "user.name"]).strip()


def _get_email() -> str:
    from os import environ

    from dda.tools.git import Git
    from dda.utils.process import SubprocessRunner

    if email := environ.get(Git.AUTHOR_EMAIL_ENV_VAR):
        return email

    return SubprocessRunner.static_capture(["git", "config", "--global", "--get", "user.email"]).strip()


class UserConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [user]
    name = "U.N. Owen"
    email = "void@some.where"
    ```
    ///
    """

    # Default username and email are fetched from git config
    name: str = field(default_factory=_get_name)
    email: str = field(default_factory=_get_email)
