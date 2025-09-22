# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dda.tools.bazel import query_accepting_commands, target_accepting_commands

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from dda.cli.application import Application
    from dda.utils.fs import Path


class TestArgLengthLimits:
    @pytest.mark.parametrize("command", sorted(target_accepting_commands()))
    def test_ambiguous_targets(self, app: Application, command: str) -> None:
        with (
            pytest.raises(ValueError, match="Bazel arguments must come after the `--` separator"),
            app.tools.bazel.execution_context([command, "//..."]),
        ):
            pass

    @pytest.mark.parametrize("command", sorted(query_accepting_commands()))
    def test_ambiguous_query(self, app: Application, command: str) -> None:
        with (
            pytest.raises(ValueError, match="Bazel arguments must come after the `--` separator"),
            app.tools.bazel.execution_context([command, "deps(//foo)"]),
        ):
            pass

    def test_targets_arg_file(self, app: Application, bazel_on_path: Path, mocker: MockerFixture) -> None:
        writer = mocker.MagicMock()
        writer.name = "targets.txt"
        mocker.patch(
            "tempfile.NamedTemporaryFile",
            return_value=mocker.MagicMock(__enter__=lambda *_, **__: writer, __exit__=lambda *_, **__: None),
        )
        with app.tools.bazel.execution_context(["build", "--foo", "--", "//foo", "//bar"]) as context:
            assert context.command == [str(bazel_on_path), "build", "--foo", "--target_pattern_file", "targets.txt"]
            writer.write.assert_called_once_with("//foo\n//bar")

    def test_query_arg_file(self, app: Application, bazel_on_path: Path, mocker: MockerFixture) -> None:
        writer = mocker.MagicMock()
        writer.name = "query.txt"
        mocker.patch(
            "tempfile.NamedTemporaryFile",
            return_value=mocker.MagicMock(__enter__=lambda *_, **__: writer, __exit__=lambda *_, **__: None),
        )
        with app.tools.bazel.execution_context(["query", "--foo", "--", "deps(//foo)"]) as context:
            assert context.command == [str(bazel_on_path), "query", "--foo", "--query_file", "query.txt"]
            writer.write.assert_called_once_with("deps(//foo)")
