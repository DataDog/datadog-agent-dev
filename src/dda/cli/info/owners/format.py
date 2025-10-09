# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.utils.fs import Path


def format_path_for_codeowners(path: Path) -> str:
    """
    Format a path for use with the codeowners library.

    The codeowners library expects paths to be in POSIX format (even on Windows).
    Moreover, contrary to pathlib, trailing slashes have a special meaning in codeowners:
    - /some/path.ext refers to a file named "path" in the "some" directory
    - /some/path.ext/ refers to a directory named "path.ext" in the "some" directory
    > These two paths would be equal as pathlib.Path objects.

    To avoid this, we check if the path refers to a directory and add a trailing slash if it does.
    """
    root = path.as_posix()

    if path.exists():
        if path.is_dir():
            return f"{root}/"
        return root

    msg = f"Path {path} does not exist"
    raise ValueError(msg)
