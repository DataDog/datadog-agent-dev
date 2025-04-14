# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import subprocess
from functools import cache
from pathlib import Path

from markdown.preprocessors import Preprocessor
from rich.console import Console
from rich.tree import Tree


@cache
def variable_replacements():
    return {
        f"<<<{variable}>>>": replacement
        for variable, replacement in (
            # Current version
            ("DDA_VERSION", get_dda_version()),
            ("DDA_ROOT_TREE", get_dda_root_tree()),
        )
    }


def get_dda_version():
    env = dict(os.environ)
    # Ignore the current documentation environment so that the version
    # command can execute as usual in the default build environment
    env.pop("HATCH_ENV_ACTIVE", None)

    output = subprocess.check_output(["hatch", "--no-color", "version"], env=env).decode("utf-8").strip()  # noqa: S607

    version = output.replace("dev", "")
    parts = list(map(int, version.split(".")))

    semver_parts = 3
    major, minor, patch = parts[:semver_parts]
    if len(parts) > semver_parts:
        patch -= 1

    return f"{major}.{minor}.{patch}"


def get_dda_root_tree():
    relative_path = "src/dda/cli"
    tree = Tree(relative_path)
    for path in Path(relative_path).iterdir():
        if path.joinpath("__init__.py").is_file():
            tree.add(path.name.replace("_", "-"))

    console = Console()
    with console.capture() as capture:
        console.print(tree)

    return capture.get().strip()


class VariableInjectionPreprocessor(Preprocessor):
    def run(self, lines):  # noqa: PLR6301
        markdown = "\n".join(lines)
        for variable, replacement in variable_replacements().items():
            markdown = markdown.replace(variable, replacement)

        return markdown.splitlines()
