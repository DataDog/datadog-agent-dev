# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dda.utils.fs import Path

if TYPE_CHECKING:
    from dda.cli.application import Application


@pytest.fixture
def temp_repo(app: Application, tmp_path: Path) -> Path:
    repo_path = Path(tmp_path) / "dummy-repo"
    repo_path.mkdir()
    app.subprocess.capture(["git", "init", "--initial-branch", "main"], cwd=str(repo_path))
    return repo_path
