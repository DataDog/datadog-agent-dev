# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field

from dda.utils.fs import Path


def default_data_dir() -> Path:
    import platformdirs

    return Path(platformdirs.user_data_dir("dda", appauthor=False))


def default_cache_dir() -> Path:
    import platformdirs

    return Path(platformdirs.user_cache_dir("dda", appauthor=False))


class StorageDirs(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [storage]
    data = "/path/to/data"
    cache = "/path/to/cache"
    ```
    ///
    """

    data: Path = field(default_factory=default_data_dir)
    """
    This is the directory that is used to persist data. By default it is set to one of the
    following platform-specific directories:

    Platform | Directory
    --- | ---
    macOS | `~/Library/Application Support/dd-agent-dev`
    Windows | `%USERPROFILE%\\AppData\\Local\\dd-agent-dev`
    Linux | `$XDG_DATA_HOME/dd-agent-dev` (the [XDG_DATA_HOME](https://specifications.freedesktop.org/basedir-spec/latest/#variables) environment variable defaults to `~/.local/share` on Linux)

    You can select a custom path to the directory using the `--data-dir` [root option](../cli/commands.md#dda) or
    by setting the [ConfigEnvVars.DATA][dda.config.constants.ConfigEnvVars.DATA] environment variable.
    """
    cache: Path = field(default_factory=default_cache_dir)
    """
    This is the directory that is used to cache data. By default it is set to one of the
    following platform-specific directories:

    Platform | Directory
    --- | ---
    macOS | `~/Library/Caches/dd-agent-dev`
    Windows | `%USERPROFILE%\\AppData\\Local\\dd-agent-dev\\Cache`
    Linux | `$XDG_CACHE_HOME/dd-agent-dev` (the [XDG_CACHE_HOME](https://specifications.freedesktop.org/basedir-spec/latest/#variables) environment variable defaults to `~/.cache` on Linux)

    You can select a custom path to the directory using the `--cache-dir` [root option](../cli/commands.md#dda) or
    by setting the [ConfigEnvVars.CACHE][dda.config.constants.ConfigEnvVars.CACHE] environment variable.
    """

    def join(self, *parts: str) -> StorageDirs:
        """
        Join the storage directories with the given parts.

        Parameters:
            parts: The parts to join.

        Returns:
            A new `StorageDirs` instance with the joined paths.
        """
        return StorageDirs(
            data=self.data.joinpath(*parts),
            cache=self.cache.joinpath(*parts),
        )
