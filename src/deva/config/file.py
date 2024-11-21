# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import tomllib
from functools import cached_property
from typing import TYPE_CHECKING, Any

from deva.config.model import construct_model, get_default_toml_data
from deva.config.utils import scrub_config
from deva.utils.fs import Path

if TYPE_CHECKING:
    from deva.config.model import RootConfig


class ConfigFile:
    def __init__(self, path: str | None = None) -> None:
        self.__path: str | None = path

    @cached_property
    def path(self) -> Path:
        if self.__path is not None:
            return Path(self.__path)

        return self.get_default_location()

    @cached_property
    def data(self) -> dict[str, Any]:
        return self.__load()

    @cached_property
    def model(self) -> RootConfig:
        return construct_model(self.data)

    def save(self, data: dict[str, Any] | None = None) -> None:
        import tomlkit

        content = tomlkit.dumps(self.data if data is None else data)
        self.path.parent.ensure_dir()
        self.path.write_atomic(content, "w", encoding="utf-8")

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def read_scrubbed(self) -> str:
        import tomlkit

        config = self.__load()
        scrub_config(config)

        return tomlkit.dumps(config)

    def restore(self) -> None:
        from contextlib import suppress

        self.save(get_default_toml_data())
        with suppress(AttributeError):
            del self.model
        with suppress(AttributeError):
            del self.data

    @classmethod
    def get_default_location(cls) -> Path:
        from platformdirs import user_data_dir

        return Path(user_data_dir("dd-agent-dev", appauthor=False)) / "config.toml"

    def __load(self) -> dict[str, Any]:
        return tomllib.loads(self.read())
