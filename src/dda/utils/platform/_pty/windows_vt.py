# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import winpty

# The current implementation linearly checks each supported query with
# `startswith()`, which stays fast while this table is small. For example, when
# the parser reaches an escape sequence such as `\x1b[6n`, it checks the known
# queries in order against the remaining suffix until one matches and then emits
# the configured reply.
#
# If we ever grow this into a much larger set, the next optimization would be
# to group queries by prefix after the leading ESC/CSI bytes so we can narrow
# the candidate set earlier. For example, `\x1b[c`, `\x1b[5n`, and `\x1b[6n`
# currently all share the `\x1b[` prefix, but a future matcher could branch on
# the next byte(s) before doing exact `startswith()` checks.
VT_QUERY_REPLIES = {
    # DA1: ask the terminal to report its primary device attributes.
    "\x1b[c": "\x1b[?1;0c",
    # DSR (status): ask whether the terminal is ready/OK.
    "\x1b[5n": "\x1b[0n",
    # DSR (cursor): ask for the current cursor position report.
    "\x1b[6n": "\x1b[0;0R",
}
# Potential future candidates if we see real-world need:
# - "\x1b[>c": secondary device attributes query
# - "\x1b[18t": report terminal size in characters


class WinPtyAdapter:
    def __init__(self, pty: winpty.PTY) -> None:
        self._pty = pty

    def spawn(self, appname: str, *, cmdline: str | None, cwd: str | None, env: str | None) -> bool:
        return self._pty.spawn(appname, cmdline=cmdline, cwd=cwd, env=env)

    def read(self, *, blocking: bool = False) -> str:
        return self._pty.read(blocking=blocking)

    def write(self, data: str) -> int:
        return self._pty.write(data)

    def isalive(self) -> bool:
        return self._pty.isalive()

    def iseof(self) -> bool:
        return self._pty.iseof()

    def get_exitstatus(self) -> int | None:
        return self._pty.get_exitstatus()

    def cancel_io(self) -> None:
        cancel_io = getattr(self._pty, "cancel_io", None)
        if cancel_io is not None:
            cancel_io()

    @property
    def pid(self) -> int | None:
        return self._pty.pid


class WindowsVtShim:
    def __init__(self) -> None:
        self._pending = ""

    def process(self, text: str) -> tuple[str, tuple[str, ...]]:
        if "\x1b" not in text and not self._pending:
            return text, ()

        data = self._pending + text
        self._pending = ""
        output_parts: list[str] = []
        replies: list[str] = []
        i = 0
        while i < len(data):
            if data[i] != "\x1b":
                next_escape = data.find("\x1b", i)
                if next_escape == -1:
                    output_parts.append(data[i:])
                    break

                output_parts.append(data[i:next_escape])
                i = next_escape
                continue

            remainder = data[i:]
            for query, reply in VT_QUERY_REPLIES.items():
                if remainder.startswith(query):
                    replies.append(reply)
                    i += len(query)
                    break
            else:
                if any(query.startswith(remainder) for query in VT_QUERY_REPLIES):
                    self._pending = remainder
                    break

                output_parts.append("\x1b")
                i += 1

        return "".join(output_parts), tuple(replies)

    def finish(self) -> str:
        pending = self._pending
        self._pending = ""
        return pending
