# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from tests.tools.conftest import clear_cached_config

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


def test_author_details(app: Application) -> None:  # noqa: ARG001
    clear_cached_config(app)
    assert app.tools.git.author_name == "Foo Bar"
    assert app.tools.git.author_email == "foo@bar.baz"
