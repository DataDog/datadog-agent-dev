# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT


from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self

from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Iterable


DEFAULT_TAG_LIBRARY_FILE = Path(".dda/build/go_tags.json")


class BuildTagManager:
    """
    A library of Go build tags.
    """

    __instances: ClassVar[dict[str, Self]] = {}

    def __new__(cls, key: str, *args: Any, **kwargs: Any) -> Self:
        if cls.__instances.get(key) is None:
            cls.__instances[key] = super().__new__(cls, *args, **kwargs)
        return cls.__instances[key]

    def __init__(self, key: str) -> None:
        self.key = key

        self.tags: set[str] = set()
        self.configurations: dict[str, set[str]] = {}

    @classmethod
    def load(cls, file: Path = DEFAULT_TAG_LIBRARY_FILE) -> Self:
        import json

        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        data_keys = data.keys()
        if data_keys != {"key", "tags", "configurations"}:
            msg = f"Invalid data: {data}"
            raise ValueError(msg)

        key = data["key"]
        if key in cls.__instances:
            msg = f"BuildTagManager for `{key}` already defined."
            raise ValueError(msg)

        res = cls(key)
        res.extend_tags(data["tags"])
        res.update_configurations(data["configurations"])

        return res

    def extend_tags(self, tags: Iterable[str]) -> None:
        self.tags.update(tags)

    def add_tag(self, tag: str) -> None:
        self.extend_tags([tag])

    def update_configurations(self, configurations: dict[str, Iterable[str]]) -> None:
        used_tags: set[str] = set()
        used_tags.update(*configurations.values())
        missing_tags = used_tags - self.tags
        if missing_tags:
            msg = f"Cannot add configurations: Tags `{missing_tags}` not found in available tags. Available tags: `{self.tags}`"
            raise ValueError(msg)

        new_names = set(configurations.keys())
        existing_names = set(self.configurations.keys())
        overlap = existing_names.intersection(new_names)
        if overlap:
            msg = f"Cannot add configurations: Names `{overlap}` already defined. Available names: `{existing_names}`"
            raise ValueError(msg)

        self.configurations.update({name: set(tags) for name, tags in configurations.items()})

    def add_configuration(self, name: str, tags: set[str]) -> None:
        self.update_configurations({name: tags})
