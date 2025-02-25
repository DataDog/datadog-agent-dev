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
    data: Path = field(default_factory=default_data_dir)
    cache: Path = field(default_factory=default_cache_dir)

    def join(self, *parts: str) -> StorageDirs:
        return StorageDirs(
            data=self.data.joinpath(*parts),
            cache=self.cache.joinpath(*parts),
        )
