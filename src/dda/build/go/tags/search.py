# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.utils.fs import Path

# Precompiled regex for Go file build constraints (e.g., // +build tag, //go:build expr)
BUILD_CONSTRAINT_LINE_PATTERN = re.compile(r"^//go:build\s+([\w|&!(). ]+)$")

# Precompiled regex for valid go tags, extracting them from a build constraint expression
BUILD_CONSTRAINT_TAG_PATTERN = re.compile(r"[^ &()|!]*")


def _get_build_constraint_expr(file_contents: str) -> str | None:
    for line in file_contents.splitlines():
        match = BUILD_CONSTRAINT_LINE_PATTERN.fullmatch(line.strip())
        if match:
            return match.group(1)
    return None


def _parse_build_constraint_expr(expr: str) -> set[str]:
    result = set(BUILD_CONSTRAINT_TAG_PATTERN.findall(expr))
    result.discard("")
    return result


def search_build_tags(root: Path, *, exclude_patterns: list[re.Pattern] | None = None) -> dict[str, set[Path]]:
    """
    Search for build tags in the repository.
    Recursively explore all `.go` files under the root directory and collect the build tags used in the files.

    Args:
        root: The root directory to search for build tags.
        exclude_patterns: A list of regular expressions to exclude files from the search.

    Returns:
        A dictionary mapping build tags to the set of paths where the build tag is used.
    """
    # Explicitely check here, otherwise the `root.walk()` method will return an empty iterator
    if not (root.exists() and root.is_dir()):
        msg = f"Root directory {root} does not exist or is not a directory"
        raise ValueError(msg)

    if exclude_patterns is None:
        exclude_patterns = []

    tag_to_paths: defaultdict[str, set[Path]] = defaultdict(set)

    for cur, dirs, files in root.walk():
        # Only consider .go files
        to_consider = [cur / file for file in files if file.endswith(".go")]

        # Pop any directory matching an exclude pattern
        # Include a trailing slash in the string to match, in case the pattern was specified with one
        dirs[:] = [d for d in dirs if not any(pattern.search(str(cur / d) + "/") for pattern in exclude_patterns)]

        for path in to_consider:
            content = path.read_text(encoding="utf-8")
            expr = _get_build_constraint_expr(content)
            if not expr:
                # File does not contain a build constraint expression
                continue

            tags = _parse_build_constraint_expr(expr)
            for tag in tags:
                tag_to_paths[tag].add(path.relative_to(root))

    return tag_to_paths
