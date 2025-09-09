# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import random
from os import environ
from typing import TYPE_CHECKING

from dda.utils.git.constants import GitEnvVars

if TYPE_CHECKING:
    from collections.abc import Callable

    from dda.cli.application import Application
    from dda.utils.fs import Path


def test_basic(
    app: Application, temp_repo: Path, create_commit_dummy_file: Callable[[Path | str, str, str], None]
) -> None:
    with temp_repo.as_cwd():
        assert app.tools.git.run(["status"]) == 0
        random_key = random.randint(1, 1000000)
        create_commit_dummy_file("testfile.txt", "test", f"Initial commit: {random_key}")
        assert f"Initial commit: {random_key}" in app.tools.git.capture(["log", "-1", "--oneline"])


def test_author_details(app: Application, mocker) -> None:  # type: ignore[no-untyped-def]
    # Test 1: Author details coming from env vars, set in conftest.py
    assert app.tools.git.author_name == "Foo Bar"
    assert app.tools.git.author_email == "foo@bar.baz"
    # Clear the cached properties
    del app.tools.git.author_name
    del app.tools.git.author_email
    # Test 2: Author details coming from git config, not set in conftest.py
    environ.pop(GitEnvVars.AUTHOR_NAME)
    environ.pop(GitEnvVars.AUTHOR_EMAIL)
    mocker.patch("dda.tools.git.Git.capture", return_value="Foo Bar 2")
    assert app.tools.git.author_name == "Foo Bar 2"
    mocker.patch("dda.tools.git.Git.capture", return_value="foo@bar2.baz")
    assert app.tools.git.author_email == "foo@bar2.baz"
