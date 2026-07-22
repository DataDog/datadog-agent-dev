# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from msgspec import Struct, field

from dda.utils.git.constants import GitEnvVars

if TYPE_CHECKING:
    from dda.utils.fs import Path


def _get_name_from_git() -> str:
    from os import environ

    if name := environ.get(GitEnvVars.AUTHOR_NAME):
        return name

    import subprocess

    command = ["git", "config", "--global", "--get", "user.name"]

    try:
        return subprocess.run(
            command,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _get_email_from_git() -> str:
    from os import environ

    if name := environ.get(GitEnvVars.AUTHOR_EMAIL):
        return name

    import subprocess

    command = ["git", "config", "--global", "--get", "user.email"]

    try:
        return subprocess.run(
            command,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


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


class GitAuthorConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.git.author]
    name = "U.N. Owen"
    email = "void@some.where"
    ```
    ///
    """

    name: str = field(default_factory=_get_name_from_git)
    email: str = field(default_factory=_get_email_from_git)


class GitConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.git]
    ...
    ```
    ///
    """

    author: GitAuthorConfig = field(default_factory=GitAuthorConfig)


def _query_go_envvar(var_name: str) -> str | None:
    from os import environ

    if name := environ.get(GitEnvVars.AUTHOR_EMAIL):
        return name

    import subprocess

    command = ["go", "env", var_name]

    try:
        return subprocess.run(
            command,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def _get_default_gopath() -> Path:
    from dda.utils.fs import Path

    result_raw = _query_go_envvar("GOPATH")
    result = Path(result_raw) if result_raw else Path.home() / "go"
    return result.expanduser().resolve()


def _get_default_gocache() -> Path:
    from dda.utils.fs import Path

    result_raw = _query_go_envvar("GOCACHE")
    if not result_raw:
        from platform import system

        result_raw = {
            "linux": "~/.cache/go-build",
            "darwin": "~/Library/Caches/go-build",
            "windows": "~\\AppData\\Local\\go-build",
        }.get(system().lower(), "~/.cache/go-build")
    return Path(result_raw).expanduser().resolve()


class GoConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [tools.go]
    gopath = "/home/user/go"
    gocache = "~/.cache/go-build"
    ```
    ///
    """

    gopath: str = field(default_factory=lambda: str(_get_default_gopath()))
    gocache: str = field(default_factory=lambda: str(_get_default_gocache()))


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
    go: GoConfig = field(default_factory=GoConfig)
