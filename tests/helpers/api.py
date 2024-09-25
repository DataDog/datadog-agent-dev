# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from datetime import UTC, datetime
from textwrap import dedent as _dedent


def dedent(text: str) -> str:
    return _dedent(text[1:])


def remove_trailing_spaces(text: str) -> str:
    return "".join(f"{line.rstrip()}\n" for line in text.splitlines(True))


def get_current_timestamp() -> float:
    return datetime.now(UTC).timestamp()


def assert_output_match(output: str, pattern: str, *, exact: bool = True) -> None:
    flags = re.MULTILINE if exact else re.MULTILINE | re.DOTALL
    assert re.search(dedent(pattern), output, flags=flags) is not None, output
