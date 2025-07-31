# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from functools import cache


def remove_ansi(text: str) -> str:
    """
    This strips out ANSI escape sequences from the given text.

    /// note
    Not every sequence is supported.
    ///
    """
    from dda.utils.terminal._ansi import remove_ansi

    return remove_ansi(text)


@cache
def terminal_size() -> os.terminal_size:
    """
    This returns the same value as [get_terminal_size][dda.utils.terminal.get_terminal_size] but the first call is cached.
    """
    return get_terminal_size()


def get_terminal_size(fallback: tuple[int, int] = (80, 24)) -> os.terminal_size:  # no cov
    """
    This is a copy of the [shutil.get_terminal_size][] function from the standard library.
    This is required to properly configure the CLI at startup but importing `shutil` is costly.
    """
    # columns, lines are the working values
    try:
        columns = int(os.environ["COLUMNS"])
    except (KeyError, ValueError):
        columns = 0

    try:
        lines = int(os.environ["LINES"])
    except (KeyError, ValueError):
        lines = 0

    # only query if necessary
    if columns <= 0 or lines <= 0:
        try:
            size = os.get_terminal_size(sys.__stdout__.fileno())  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            # stdout is None, closed, detached, or not a terminal, or
            # os.get_terminal_size() is unsupported
            size = os.terminal_size(fallback)
        if columns <= 0:
            columns = size.columns or fallback[0]
        if lines <= 0:
            lines = size.lines or fallback[1]

    return os.terminal_size((columns, lines))
