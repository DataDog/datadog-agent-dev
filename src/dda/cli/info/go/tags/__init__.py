# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.utils.fs import Path

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="Query the list of Go build tags existing in the repository.",
)
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True, path_type=Path),
    default=Path.cwd(),
    # NOTE: Should we default to the root of the currently-open git repository?
    help="The repository path to use. Defaults to the current working directory.",
)
@click.option("--json", "-j", is_flag=True, help="Format the output as JSON.")
@click.option("--map", "-m", is_flag=True, help="Map the tags to the paths where they are used.")
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="Exclude files or directories from the search using a regular expression. Can be specified multiple times.",
)
@pass_app
def cmd(app: Application, *, repo: Path, json: bool, map: bool, exclude: list[str]) -> None:  # noqa: A002
    import re

    from dda.build.go.tags.search import search_build_tags

    result_raw = search_build_tags(repo, exclude_patterns=[re.compile(pattern) for pattern in exclude])

    # Need to convert the set[Path] to a list[str] to be able to serialize to JSON
    # Sort the inner list elements alphabetically for consistent output
    result_map = {tag: sorted(str(path) for path in paths) for tag, paths in result_raw.items()}
    result_list = sorted(result_map.keys(), key=lambda x: len(result_map[x]), reverse=True)

    if json:
        from json import dumps

        result = result_map if map else result_list
        app.output(dumps(result))
        return

    # If outputting for humans, display the tags in a table
    # This table is sorted by the most frequently used tags first
    if len(result_list) == 0:
        app.display("No build tags found.")
        return

    if not map:
        app.display("\n".join(result_list))
        return

    from collections import OrderedDict

    # Order the tags by most-used first (by "count"), descending
    result_human = OrderedDict([
        (tag, {"count": len(result_map[tag]), "paths": _regroup_paths_by_longest_common_prefix(result_map[tag])})
        for tag in result_list
    ])
    app.display_table(result_human)
    return


def _regroup_paths_by_longest_common_prefix(paths: list[str]) -> str:
    if len(paths) == 0:
        return ""

    if len(paths) == 1:
        return paths[0]

    import os

    # Use commonpath to get the deepest common directory
    common_dir = os.path.commonpath(paths)
    if not common_dir:
        return ", ".join(paths)

    # Extract just the filenames (or remaining path parts) after the common directory
    remaining_parts = [os.path.relpath(path, common_dir) for path in paths]

    # Return `common_dir/{file1, file2, ...}`
    return f"{common_dir}/{{{', '.join(remaining_parts)}}}"
