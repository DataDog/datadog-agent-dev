# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING

from dda.env.dev.git_ssh import PERSONAL_SELECTOR_FILE
from dda.tools.ssh import PublicKey
from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dda.cli.application import Application


def migrate_legacy_personal_key(app: Application) -> None:
    """Offer a one-time migration of the old personal SSH identity."""
    ssh_dir = app.tools.ssh.config_dir
    old_public = ssh_dir / "dda.pub"
    new_public = ssh_dir / PERSONAL_SELECTOR_FILE
    if new_public.exists() or new_public.is_symlink() or not old_public.is_file():
        return
    app.display(f"Found `{old_public}`.")
    if not app.console.is_interactive:
        app.display(f"Run `dda env dev ssh doctor` to migrate it to ~/.ssh/{PERSONAL_SELECTOR_FILE}.")
        return

    try:
        if not _migrate(app, old_public, new_public):
            return
    except (OSError, UnicodeError, ValueError) as error:
        app.abort(f"Could not migrate the personal SSH key: {error}")
    app.display(
        f"Migrated the personal SSH key to ~/.ssh/{PERSONAL_SELECTOR_FILE}. "
        "Recreate existing developer environments to use it."
    )


def _migrate(app: Application, old_public: Path, new_public: Path) -> bool:
    old_private = old_public.with_suffix("")
    new_private = new_public.with_suffix("")
    has_private = old_private.is_file()
    if not has_private and old_private.exists():
        msg = f"`{old_private}` is not a file."
        raise ValueError(msg)
    moves = [(old_public, new_public)]
    if has_private:
        moves.insert(0, (old_private, new_private))
    app.display("Migration will:")
    for source, destination in moves:
        if destination.exists() or destination.is_symlink():
            msg = f"Refusing to overwrite `{destination}`."
            raise ValueError(msg)
        app.display(f"  - Rename `{source}` to `{destination}`.")

    agent_keys = app.tools.ssh.get_agent_keys()
    selector = app.tools.ssh.inspect_public_key_file(old_public)
    key = selector.result
    if not isinstance(key, PublicKey):
        # Selector failures describe missing or invalid files.
        raise ValueError(selector.resolve(agent_keys))  # noqa: TRY004
    loaded = key.fingerprint in agent_keys
    if not loaded:
        if not has_private:
            msg = f"Load {key.fingerprint} in the host SSH agent first; `{old_private}` is missing."
            raise ValueError(msg)
        app.display(f"  - Load {key.fingerprint} into the host SSH agent from `{old_private}`.")
    git_edits = _git_config_edits(app, old_public.parent)
    ssh_edits = _ssh_config_edits(app, old_public.parent)
    originals = {path: path.read_bytes() for path, _, _ in git_edits}
    originals.update({path: path.read_bytes() for path in ssh_edits})

    if not app.confirm("Migrate?", default=False):
        return False

    if not loaded:
        # Agent identities are selected by fingerprint, so renaming the files does not require removing any keys.
        process = app.subprocess.attach([app.tools.ssh.agent_path, str(old_private)], check=False, abort_on_error=False)
        if process.returncode or key.fingerprint not in app.tools.ssh.get_agent_keys():
            msg = "The personal key could not be loaded in the host SSH agent. The key files have not been renamed."
            raise ValueError(msg)

    renamed: list[tuple[Path, Path]] = []
    try:
        for source, destination in moves:
            source.rename(destination)
            renamed.append((source, destination))
        for path, old_value, new_value in git_edits:
            app.tools.git.capture([
                "config",
                "--file",
                str(path),
                "--fixed-value",
                "--replace-all",
                "user.signingKey",
                new_value,
                old_value,
            ])
        for path, contents in ssh_edits.items():
            path.write_atomic(contents, "wb")
    except BaseException:
        try:
            for path, contents in originals.items():
                if path.read_bytes() != contents:
                    path.write_atomic(contents, "wb")
        finally:
            for source, destination in reversed(renamed):
                destination.rename(source)
        raise
    return True


def _renamed_path(value: str, ssh_dir: Path) -> str | None:
    path = _expand_path(value, ssh_dir.parent)
    for name in ("dda", "dda.pub"):
        if path == ssh_dir / name:
            new_name = name.replace("dda", "dd", 1)
            return value[: -len(name)] + new_name if value.casefold().endswith(name) else str(ssh_dir / new_name)
    return None


def _expand_path(value: str, home: Path) -> Path:
    value = value.replace("%d", str(home))
    if value.startswith(("~/", "~\\")):
        return home / value[2:]
    return Path(value).expand()


def _git_config_edits(app: Application, ssh_dir: Path) -> list[tuple[Path, str, str]]:
    # Read every user include, including inactive conditional profiles, before renaming their referenced key.
    output = app.tools.git.capture(["config", "--no-includes", "--null", "--show-scope", "--show-origin", "--list"])
    fields = output.removesuffix("\0").split("\0") if output else []
    pending = []
    for index in range(0, len(fields), 3):
        scope, origin, _ = fields[index : index + 3]
        if scope in {"global", "local", "worktree"} and origin.startswith("file:"):
            pending.append(Path(origin.removeprefix("file:")))
    edits: list[tuple[Path, str, str]] = []
    for path in _walk_files(pending):
        output = app.tools.git.capture(["config", "--file", str(path), "--no-includes", "--null", "--list"])
        for record in output.split("\0"):
            key, _, value = record.partition("\n")
            if key == "user.signingkey" and (replacement := _renamed_path(value, ssh_dir)) is not None:
                app.display(f"  - Update Git user.signingKey in `{path}` from `{value}` to `{replacement}`.")
                edits.append((path, value, replacement))
            elif key == "include.path" or (key.startswith("includeif.") and key.endswith(".path")):
                included = _expand_path(value, ssh_dir.parent)
                pending.append(included if included.is_absolute() else path.parent / included)
    return edits


def _ssh_config_edits(app: Application, ssh_dir: Path) -> dict[Path, bytes]:
    from glob import glob

    pending = [ssh_dir / "config"]
    edits: dict[Path, bytes] = {}
    for path in _walk_files(pending):
        contents = path.read_bytes().decode("utf-8")
        lines = []
        for line in contents.splitlines(keepends=True):
            updated_line = line
            match = re.match(r"([ \t]*([\w]+)[ \t=]+)(.*)", line)
            if match is not None and (directive := match[2].casefold()) in {"identityfile", "include"}:
                lexer = shlex.shlex(match[3], posix=True)
                lexer.whitespace_split = True
                lexer.escape = ""
                arguments = list(lexer)
                if directive == "include":
                    for argument in arguments:
                        included = _expand_path(argument, ssh_dir.parent)
                        pattern = included if included.is_absolute() else ssh_dir / included
                        pending.extend(Path(included_file) for included_file in glob(str(pattern)))
                elif len(arguments) == 1 and (replacement := _renamed_path(arguments[0], ssh_dir)) is not None:
                    updated_line = match[1] + line[len(match[1]) :].replace(arguments[0], replacement, 1)
            lines.append(updated_line)
        updated = "".join(lines)
        if updated != contents:
            app.display(f"  - Update SSH IdentityFile references in `{path}`.")
            edits[path] = updated.encode("utf-8")
    return edits


def _walk_files(pending: list[Path]) -> Iterator[Path]:
    # Callers append discovered includes to `pending` while iterating.
    visited: set[Path] = set()
    while pending:
        path = pending.pop().resolve()
        if path in visited or not path.is_file():
            continue
        visited.add(path)
        yield path
