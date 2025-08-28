# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Literal

from msgspec import Struct, field

from dda.tools.git import Git


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

    @staticmethod
    def _get_username_from_git() -> str:
        from os import environ
        from subprocess import CalledProcessError

        if env_name := environ.get(Git.AUTHOR_NAME_ENV_VAR):
            return env_name

        try:
            return Git._query_author_name()  # noqa: SLF001
        except CalledProcessError:
            return ""

    @staticmethod
    def _get_email_from_git() -> str:
        from os import environ
        from subprocess import CalledProcessError

        if env_email := environ.get(Git.AUTHOR_EMAIL_ENV_VAR):
            return env_email

        try:
            return Git._query_author_email()  # noqa: SLF001
        except CalledProcessError:
            return ""

    # TODO: Do we really want to tie this to git? Should we have a separate section for user info instead?
    # TODO: Do we really want this here ? We are not so much configuring git
    username: str = field(default_factory=_get_username_from_git)
    user_email: str = field(default_factory=_get_email_from_git)


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
