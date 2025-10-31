# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json

import pytest

from dda.build.go.tags import BuildTagManager
from dda.utils.fs import Path

TEST_TAG_LIBRARIES = {
    "library_1": Path(__file__).parent / "fixtures" / "tag_libraries" / "library_1.json",
    "library_2": Path(__file__).parent / "fixtures" / "tag_libraries" / "library_2.json",
}


@pytest.fixture
def example_manager():
    res = BuildTagManager("test")
    res.extend_tags(["a", "b", "c"])
    res.update_configurations({"example_config": ["a", "b"]})
    return res


class TestBuildTagManager:
    @pytest.mark.parametrize("file", TEST_TAG_LIBRARIES.values())
    def test_load(self, file):
        manager = BuildTagManager.load(file)
        raw = json.load(file.open("r", encoding="utf-8"))
        assert manager.key == raw["key"]
        assert manager.tags == set(raw["tags"])
        assert manager.configurations == {k: set(v) for k, v in raw["configurations"].items()}

    def test_invalid_configurations(self, example_manager):
        with pytest.raises(
            ValueError,
            match="Cannot add configurations: Tags `.*` not found in available tags. Available tags: `.*`",
        ):
            example_manager.update_configurations({"example_config_2": ["d", "e", "f"]})
        with pytest.raises(
            ValueError,
            match="Cannot add configurations: Names `.*` already defined. Available names: `.*`",
        ):
            example_manager.update_configurations({"example_config": ["a", "b"]})

    def test_update_configurations(self, example_manager):
        example_manager.extend_tags(["d", "e", "f", "g"])
        example_manager.update_configurations({"example_config_2": ["d", "e"], "example_config_3": ["f", "g"]})
        assert example_manager.configurations.get("example_config_2") == {"d", "e"}
        assert example_manager.configurations.get("example_config_3") == {"f", "g"}

    def test_extend_tags(self, example_manager):
        example_manager.extend_tags(["x", "y"])
        assert "x" in example_manager.tags
        assert "y" in example_manager.tags
