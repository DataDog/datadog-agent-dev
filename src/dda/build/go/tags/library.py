# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT


from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Self

from msgspec import Struct

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dda.utils.fs import Path


class BuildTagLibrary(Struct, frozen=True):
    """
    A library of Go build tags.
    Holds two attributes:
        - tags (`set[str]`): A set of Go tags that are found across Go files in the repository.
        - configurations (`dict[str, set[str]]`): A dictionary of Go build configurations, identified by string keys.
            We call a "configuration" a set of tags, or tag-exclusions (a tag prefixed by `!`).
            This can be used during a build as a shorthand for a set of tags to include or exclude.
    """

    tags: set[str]
    configurations: dict[str, set[str]]

    @staticmethod
    def __validate_configurations(tags: set[str], configurations: dict[str, Iterable[str]]) -> None:
        """Validate that a set of configurations contains only tags that are in the given set of tags."""
        used_tags: set[str] = set()
        used_tags.update(itertools.chain.from_iterable(configurations.values()))
        missing_tags = used_tags - tags
        if missing_tags:
            msg = f"Invalid configurations: Tags `{missing_tags}` not found in available tags. Available tags: `{tags}`"
            raise ValueError(msg)

    def __validate_new_configurations(self, configurations: dict[str, Iterable[str]]) -> None:
        """Validate that a set of new configurations can be added to the library: no duplicate keys, and all tags are valid."""
        new_keys = set(configurations.keys())
        existing_keys = set(self.configurations.keys())
        overlap = existing_keys.intersection(new_keys)
        if overlap:
            msg = f"Cannot add configurations: Keys `{overlap}` already defined. Available keys: `{existing_keys}`"
            raise ValueError(msg)

        self.__validate_configurations(self.tags, configurations)

    def __post_init__(self) -> None:
        self.__validate_configurations(self.tags, self.configurations)  # type: ignore[arg-type]

    @classmethod
    def load(cls, file: Path) -> Self:
        import json

        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        data_keys = data.keys()
        if data_keys != {"tags", "configurations"}:
            msg = f"Invalid data: {data}"
            raise ValueError(msg)

        return cls(tags=set(data["tags"]), configurations={k: set(v) for k, v in data["configurations"].items()})

    def extend_tags(self, tags: Iterable[str]) -> None:
        self.tags.update(tags)

    def add_tag(self, tag: str) -> None:
        self.extend_tags([tag])

    def extend_configurations(self, configurations: dict[str, Iterable[str]]) -> None:
        self.__validate_new_configurations(configurations)
        self.configurations.update({name: set(tags) for name, tags in configurations.items()})

    def add_configuration(self, name: str, tags: set[str]) -> None:
        self.extend_configurations({name: tags})


# TODO: From discussion with @pgimalac:
# - We need to be able to reference configurations in other configurations: for example the `fips-agent` configuration will be the merging of the `fips` and `agent` configurations.
#       In this paradigm a "configuration" is really just a set of tags - maybe we need another name for whatever the "end products" are ?
#       Note that some "dynamically-computed" configurations are subsequently referenced in other dynamically-computed configurations.
# - We need to be able to split the library of configurations across multiple files, such that each team can have ownership of one file and define there their own configurations. During resolution and usage though all files need to be merged into a single library.
# - Some tags that are used in configurations come from the go stdlib or dependencies - we also need to include a set of statically-defined tags that are not computed from the go files in the repository.
