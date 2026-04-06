# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app
from dda.utils.fs import Path

if TYPE_CHECKING:
    import codeowners

    from dda.cli.application import Application


def _find_existing_ancestor(path: Path) -> Path:
    """Walk up from path to find the nearest existing ancestor."""
    check = path
    while not check.exists():
        check = check.parent
    return check


def _display_result(app: Application, res: dict[str, list[str | None]], *, json: bool) -> None:
    if json:
        from json import dumps

        app.output(dumps(res))
    else:
        # Note: paths here are in POSIX format, so they will use / even on Windows
        display_res = {path: ", ".join(str(x) for x in owners) for path, owners in res.items()}
        app.display_table(display_res, stderr=False)


def _load_owners(path: Path, owners_cache: dict[Path, codeowners.CodeOwners]) -> codeowners.CodeOwners:
    if path in owners_cache:
        return owners_cache[path]

    import codeowners

    # Can raise FileNotFoundError
    owners = codeowners.CodeOwners(path.read_text(encoding="utf-8"))
    owners_cache[path] = owners
    return owners


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
    "owners_path_override",
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
def cmd(app: Application, paths: tuple[Path, ...], *, owners_path_override: Path | None, json: bool) -> None:
    """
    Gets the code owners for the specified paths.
    """
    import os

    from dda.cli.info.owners.format import format_path_for_codeowners

    cwd = Path.cwd()

    # Resolve explicit --owners path from CWD before any CWD changes
    if owners_path_override is not None:
        owners_path_override = owners_path_override.resolve()

    # Process each path with dynamic repo root detection
    res: dict[str, list[str | None]] = {}
    owners_cache: dict[Path, codeowners.CodeOwners] = {}

    errors: list[str] = []
    for path in paths:
        # Avoid resolving symlinks as they might point outside the repo
        abs_path = Path(os.path.normpath(cwd / path))

        # Determine repo root from the file's location
        try:
            repo_root = app.tools.git.get_repo_root(_find_existing_ancestor(abs_path))
        except ValueError:
            msg = f"Could not determine repo root for path: {abs_path}"
            errors.append(msg)
            continue

        repo_relative = Path(abs_path.relative_to(repo_root))

        # Load CODEOWNERS file from repo root
        try:
            owners_path = owners_path_override or repo_root / ".github" / "CODEOWNERS"
            owners = _load_owners(owners_path, owners_cache)
        except FileNotFoundError:
            msg = f"CODEOWNERS file not found for {abs_path}: {owners_path} does not exist"
            errors.append(msg)
            continue

        with repo_root.as_cwd():
            try:
                formatted_path = format_path_for_codeowners(repo_relative)
            except ValueError as e:
                errors.append(str(e))
                continue
            resolved_owners = owners.of(formatted_path)
            res[formatted_path] = [owner[1] for owner in resolved_owners] if resolved_owners else [None]

    if res:
        _display_result(app, res, json=json)

    if errors:
        app.display_error("\n".join(errors), stderr=True)
        app.abort(code=1)
