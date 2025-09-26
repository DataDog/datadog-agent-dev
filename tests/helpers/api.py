# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import shutil
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import cache
from textwrap import dedent as _dedent
from typing import TYPE_CHECKING, Any
from unittest import mock

if TYPE_CHECKING:
    from collections.abc import Generator
    from os import PathLike
    from subprocess import CompletedProcess


CallArgsT = list[tuple[tuple[Any, ...], dict[str, Any]]]


def dedent(text: str) -> str:
    return _dedent(text[1:])


def remove_trailing_spaces(text: str) -> str:
    return "".join(f"{line.rstrip()}\n" for line in text.splitlines(True))


def get_current_timestamp() -> float:
    return datetime.now(UTC).timestamp()


def assert_output_match(output: str, pattern: str, *, exact: bool = True) -> None:
    flags = re.MULTILINE if exact else re.MULTILINE | re.DOTALL
    assert re.search(dedent(pattern), output, flags=flags) is not None, output


@cache
def locate(executable: str) -> str:
    # This is used for cross-platform subprocess call assertions as our utilities
    # only resolve the executable path on Windows.
    return (shutil.which(executable) if sys.platform == "win32" else executable) or executable


@contextmanager
def hybrid_patch(target: str, *, return_values: dict[int, CompletedProcess]) -> Generator[CallArgsT, None, None]:
    calls: CallArgsT = []
    num_calls = 0

    def side_effect(*args, **kwargs):
        nonlocal num_calls

        num_calls += 1
        if num_calls in return_values:
            return return_values[num_calls]

        calls.append((args, kwargs))
        return mock.MagicMock(returncode=0)

    with mock.patch(target, side_effect=side_effect):
        yield calls


def create_binary(path: PathLike) -> None:
    shutil.copy(__existing_binary(), path)


@cache
def __existing_binary() -> str:
    import sysconfig

    # Prefer the entry point because it's very small
    return shutil.which("dda", path=sysconfig.get_path("scripts")) or sys.executable
