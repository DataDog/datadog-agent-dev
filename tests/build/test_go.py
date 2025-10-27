# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import re

import pytest

from dda.build.go.tags.library import BuildTagLibrary
from dda.build.go.tags.search import (
    _get_build_constraint_expr,  # noqa: PLC2701
    _parse_build_constraint_expr,  # noqa: PLC2701
    search_build_tags,
)
from dda.utils.fs import Path


class TestBuildTagLibrary:
    TEST_TAG_LIBRARIES = {  # noqa: RUF012
        "library_1": Path(__file__).parent / "fixtures" / "tag_libraries" / "library_1.json",
        "library_2": Path(__file__).parent / "fixtures" / "tag_libraries" / "library_2.json",
    }

    @pytest.fixture
    def example_library(self):
        return BuildTagLibrary(tags={"a", "b", "c"}, configurations={"config_1": {"a", "b"}, "config_2": {"b", "c"}})

    @pytest.mark.parametrize("file", TEST_TAG_LIBRARIES.values())
    def test_load(self, file):
        library = BuildTagLibrary.load(file)
        raw = json.load(file.open("r", encoding="utf-8"))
        assert library.tags == set(raw["tags"])
        assert library.configurations == {k: set(v) for k, v in raw["configurations"].items()}

    def test_invalid_configurations(self, example_library):
        with pytest.raises(
            ValueError,
            match="Invalid configurations: Tags `.*` not found in available tags. Available tags: `.*`",
        ):
            example_library.extend_configurations({"example_config_2": ["d", "e", "f"]})
        with pytest.raises(
            ValueError,
            match="Cannot add configurations: Keys `.*` already defined. Available keys: `.*`",
        ):
            example_library.extend_configurations({"config_1": ["a", "b"]})

    def test_extend_configurations(self, example_library):
        example_library.extend_tags(["d", "e", "f", "g"])
        example_library.extend_configurations({"config_3": ["d", "e"], "config_4": ["f", "g"]})
        assert example_library.configurations.get("config_3") == {"d", "e"}
        assert example_library.configurations.get("config_4") == {"f", "g"}

    def test_extend_tags(self, example_library):
        example_library.extend_tags(["x", "y"])
        assert "x" in example_library.tags
        assert "y" in example_library.tags


class TestBuildTagSearch:
    TEST_GO_FILES_DIR = Path(__file__).parent / "fixtures" / "go_files"
    TEST_GO_FILES = set(TEST_GO_FILES_DIR.rglob("*.go"))  # noqa: RUF012

    @pytest.fixture
    def expected_build_constraints(self):
        """Load expected build constraints from the JSON file."""
        cases_file = self.TEST_GO_FILES_DIR / "expected_constraints.json"
        with cases_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def expected_search_results(self):
        """Load expected search results from the JSON file."""
        cases_file = self.TEST_GO_FILES_DIR / "expected_search_results.json"
        with cases_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: {Path(p) for p in v} for k, v in data.items()}

    @pytest.fixture
    def parsing_testcases(self):
        """Load expected build constraint testcases from the JSON file."""
        cases_file = Path(__file__).parent / "fixtures" / "build_constraint_parsing.json"
        with cases_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.mark.parametrize("file", TEST_GO_FILES)
    def test_get_build_constraint_expr(self, file, expected_build_constraints):
        expr = _get_build_constraint_expr(file.read_text(encoding="utf-8"))
        assert expr == expected_build_constraints[str(file.relative_to(self.TEST_GO_FILES_DIR))]

    def test_parse_build_constraint_expr(self, parsing_testcases):
        for expression, expected_tags in parsing_testcases.items():
            tags = _parse_build_constraint_expr(expression)
            expected_tags = set(expected_tags)  # noqa: PLW2901
            assert tags == expected_tags, f"Failed for testcase: {expression}"

    def test_search_build_tags_basic(self, expected_search_results):
        result = search_build_tags(self.TEST_GO_FILES_DIR)
        assert result == expected_search_results

    @pytest.mark.parametrize(
        ("exclude_patterns", "paths_to_exclude"),
        [
            ([re.compile(r".*dira/.*")], [Path("dira/")]),
            (
                [re.compile(r".*subdira/.*"), re.compile(r".*dirb/.*")],
                [Path("dira/subdira"), Path("dirb/")],
            ),
        ],
    )
    def test_search_build_tags_exclude_patterns(self, expected_search_results, exclude_patterns, paths_to_exclude):
        result = search_build_tags(self.TEST_GO_FILES_DIR, exclude_patterns=exclude_patterns)
        expected_search_results = {
            k: {file for file in v if not any(file.is_relative_to(path) for path in paths_to_exclude)}
            for k, v in expected_search_results.items()
        }
        assert result == expected_search_results

    def test_search_build_tags_invalid_root(self, tmp_path):
        """Test searching with invalid root directory."""
        with pytest.raises(ValueError, match="does not exist or is not a directory"):
            search_build_tags(Path(tmp_path / "does_not_exist"))
