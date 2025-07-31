# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re

# Wikipedia appears to be the best resource:
# https://en.wikipedia.org/wiki/ANSI_escape_code

# CSI sequences with a numeric parameter
__CSI_NUM_RE = re.compile(r"\x1b\[(\d+)([A-Za-z])")

# ANSI/OSC/ESC sequences
__ANSI_OSC_RE = re.compile(
    r"""
    \x1B                      # ESC
    (?:
      \[ [0-?]* [ -/]* [@-~]  # CSI ... final byte
    | \] .*? (?:\x07|\x1B\\)  # OSC ... BEL or ESC\
    | [@-Z\\\-_]              # single-char 7-bit C1
    )
""",
    re.VERBOSE | re.DOTALL,
)


def __csi_num_repl(match: re.Match) -> str:
    count, cmd = match.groups()
    n = int(count)
    if cmd == "C":
        # cursor-forward: replace with n spaces
        return " " * n

    # Drop erase-chars, and any other CSI we don't specially handle
    return ""


def remove_ansi(text: str) -> str:
    # First expand/drop CSI-with-number commands that we can
    text = __CSI_NUM_RE.sub(__csi_num_repl, text)
    # Then strip everything else
    return __ANSI_OSC_RE.sub("", text)
