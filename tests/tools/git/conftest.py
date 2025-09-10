# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from dda.cli.application import Application
    from dda.utils.fs import Path


# Initialize a dummy repo in a temporary directory for the tests to use
@pytest.fixture
def temp_repo(app: Application, temp_dir: Path, set_config_author_details: None) -> Path:  # noqa: ARG001
    repo_path = temp_dir / "dummy-repo"
    repo_path.mkdir()  # Don't do exist_ok, the directory should not exist
    with repo_path.as_cwd():
        app.subprocess.run(["git", "init", "--initial-branch", "main"])
    return repo_path


# Create a dummy file in the repository - uses the previously initialized dummy repo and the "fixture factory" pattern
@pytest.fixture
def create_commit_dummy_file(  # type: ignore[no-untyped-def]
    app: Application,
    temp_repo: Path,
    helpers,
) -> Callable[[Path | str, str, str], None]:
    def _create_commit_dummy_file(location: Path | str, content: str, commit_message: str) -> None:
        location = temp_repo / location

        helpers.commit_file(app, file=location, message=commit_message, file_content=content)

    return _create_commit_dummy_file
