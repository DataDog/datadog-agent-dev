# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from dda.utils.fs import Path
from dda.utils.git.constants import GitEnvVars
from dda.utils.process import EnvVars

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.config.model.tools import GitAuthorConfig


def test_basic(app: Application, temp_repo: Path, helpers) -> None:  # type: ignore[no-untyped-def]
    with temp_repo.as_cwd():
        assert app.tools.git.run(["status"]) == 0
        random_key = random.randint(1, 1000000)
        helpers.commit_file(
            app, file=Path("testfile.txt"), file_content="test", message=f"Initial commit: {random_key}"
        )
        assert f"Initial commit: {random_key}" in app.tools.git.capture(["log", "-1", "--oneline"])


def test_author_details(app: Application, mocker, default_git_author: GitAuthorConfig) -> None:  # type: ignore[no-untyped-def]
    # Test 1: Author details coming from env vars, set by the fixture
    assert app.tools.git.author_name == default_git_author.name
    assert app.tools.git.author_email == default_git_author.email
    # Clear the cached properties
    del app.tools.git.author_name
    del app.tools.git.author_email
    # Test 2: Author details coming from git config, not set by the fixture
    with EnvVars({GitEnvVars.AUTHOR_NAME: "", GitEnvVars.AUTHOR_EMAIL: ""}):
        mocker.patch("dda.tools.git.Git.capture", return_value="Foo Bar 2")
        assert app.tools.git.author_name == "Foo Bar 2"
        mocker.patch("dda.tools.git.Git.capture", return_value="foo@bar2.baz")
        assert app.tools.git.author_email == "foo@bar2.baz"
