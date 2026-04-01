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


def _find_existing_ancestor(path: Path) -> Path:
    """Walk up from path to find the nearest existing ancestor."""
    check = path
    while not check.exists():
        check = check.parent
    return check


@dynamic_command(short_help="Find code owners of files and directories", features=["codeowners"])
@click.argument(
    "paths",
    type=click.Path(path_type=Path),
    required=True,
    nargs=-1,
)
@click.option(
    "--owners",
    "-f",
    "owners_filepath",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    help="Path to CODEOWNERS file",
    default=None,
)
# TODO: Make this respect any --non-interactive flag or other way to detect CI environment
@click.option(
    "--json",
    is_flag=True,
    help="Format the output as JSON",
)
@pass_app
def cmd(app: Application, paths: tuple[Path, ...], *, owners_filepath: Path | None, json: bool) -> None:
    """
    Gets the code owners for the specified paths.
    """
    import codeowners

    from dda.cli.info.owners.format import format_path_for_codeowners

    cwd = Path.cwd()

    # Resolve explicit --owners path from CWD before any CWD changes
    if owners_filepath is not None:
        owners_filepath = Path((cwd / owners_filepath).resolve())

    # Process each path with dynamic repo root detection
    res: dict[str, list[str]] = {}
    owners_cache: dict[Path, codeowners.CodeOwners] = {}

    errors: list[str] = []
    for path in paths:
        abs_path = Path((cwd / path).resolve())

        # Determine repo root from the file's location
        try:
            repo_root = app.tools.git.get_repo_root(_find_existing_ancestor(abs_path))
        except ValueError:
            msg = f"Could not determine repo root for path: {abs_path}"
            errors.append(msg)
            continue

        repo_relative = Path(abs_path.relative_to(repo_root))

        # Load CODEOWNERS (auto-detect from repo root, or use explicit)
        co_file = owners_filepath if owners_filepath is not None else repo_root / ".github" / "CODEOWNERS"
        if co_file not in owners_cache:
            try:
                owners = codeowners.CodeOwners(co_file.read_text(encoding="utf-8"))
            except FileNotFoundError:
                msg = f"CODEOWNERS file not found for {abs_path}: {co_file} does not exist"
                errors.append(msg)
                continue
            owners_cache[co_file] = owners

        with repo_root.as_cwd():
            formatted_path = format_path_for_codeowners(repo_relative)
            res[formatted_path] = [owner[1] for owner in owners_cache[co_file].of(formatted_path)]

    if res:
        if json:
            from json import dumps

            app.output(dumps(res))
        else:
            # Note: paths here are in POSIX format, so they will use / even on Windows
            display_res = {path: ", ".join(owners) for path, owners in res.items()}
            app.display_table(display_res, stderr=False)

    if errors:
        app.display_error("\n".join(errors), stderr=True)
        app.abort(code=1)
