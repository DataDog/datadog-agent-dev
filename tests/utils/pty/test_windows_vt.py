# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import io
import signal
import sys
import threading
import types
from typing import Any, cast

import pytest

from dda.utils.platform._pty.windows_vt import VT_QUERY_REPLIES, WindowsVtShim, WinPtyAdapter


class FakeWinPty:
    def __init__(self) -> None:
        self.spawn_calls: list[tuple[str, str | None, str | None, str | None]] = []
        self.read_calls = 0
        self.write_calls: list[str] = []
        self.cancelled = False
        self.pid = 42

    def spawn(
        self, appname: str, *, cmdline: str | None = None, cwd: str | None = None, env: str | None = None
    ) -> bool:
        self.spawn_calls.append((appname, cmdline, cwd, env))
        return True

    def read(self) -> str:
        self.read_calls += 1
        return "output"

    def write(self, data: str) -> int:
        self.write_calls.append(data)
        return len(data)

    def isalive(self) -> bool:
        return True

    def iseof(self) -> bool:
        return False

    def get_exitstatus(self) -> int | None:
        return 0

    def cancel_io(self) -> None:
        self.cancelled = True


def test_winpty_adapter_wraps_low_level_api():
    raw_pty = FakeWinPty()
    pty = WinPtyAdapter(raw_pty)

    assert pty.spawn("python", cmdline="-V", cwd="C:/", env="FOO=bar\0") is True
    assert pty.read() == "output"
    assert pty.write("hello") == 5
    assert pty.isalive() is True
    assert pty.iseof() is False
    assert pty.get_exitstatus() == 0
    assert pty.pid == 42

    pty.cancel_io()

    assert raw_pty.spawn_calls == [("python", "-V", "C:/", "FOO=bar\0")]
    assert raw_pty.read_calls == 1
    assert raw_pty.write_calls == ["hello"]
    assert raw_pty.cancelled is True


def test_windows_vt_shim_replies_to_known_queries():
    shim = WindowsVtShim()

    output, replies = shim.process("foo\x1b[cbar\x1b[5n\x1b[6nbaz")

    assert output == "foobarbaz"
    assert replies == (
        VT_QUERY_REPLIES["\x1b[c"],
        VT_QUERY_REPLIES["\x1b[5n"],
        VT_QUERY_REPLIES["\x1b[6n"],
    )


def test_windows_vt_shim_buffers_partial_query():
    shim = WindowsVtShim()

    output, replies = shim.process("foo\x1b[")
    assert output == "foo"
    assert replies == ()

    output, replies = shim.process("6nbar")
    assert output == "bar"
    assert replies == (VT_QUERY_REPLIES["\x1b[6n"],)


def test_windows_vt_shim_preserves_split_non_query_escape_sequence():
    shim = WindowsVtShim()

    output, replies = shim.process("\x1b[")
    assert output == ""
    assert replies == ()

    output, replies = shim.process("31mred\x1b[0m")
    assert output == "\x1b[31mred\x1b[0m"
    assert replies == ()


def test_windows_vt_shim_flushes_incomplete_tail():
    shim = WindowsVtShim()

    output, replies = shim.process("foo\x1b[")

    assert output == "foo"
    assert replies == ()
    assert shim.finish() == "\x1b["


def test_windows_vt_shim_fast_path():
    shim = WindowsVtShim()

    assert shim.process("plain text") == ("plain text", ())


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only test")
def test_windows_session_forwards_custom_stdin():
    from dda.utils.platform._pty.windows import PtySession

    class FakePty:
        def isalive(self) -> bool:
            return True

    session = PtySession.__new__(PtySession)
    session.pty = FakePty()
    writes: list[str] = []
    session._write_stdin = writes.append  # type: ignore[method-assign]

    session._forward_stdin(io.StringIO("ab"), threading.Event())

    assert writes == ["a", "b"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only test")
def test_windows_session_wait_polls_exitstatus():
    from dda.utils.platform._pty.windows import PtySession

    class FakePty:
        def __init__(self) -> None:
            self.calls = 0

        def get_exitstatus(self) -> int | None:
            self.calls += 1
            return 0 if self.calls >= 3 else None

    session = PtySession.__new__(PtySession)
    session.pty = FakePty()

    session.wait()

    assert session.pty.calls == 3


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only test")
def test_windows_session_interrupts_main_on_ctrl_c(monkeypatch: pytest.MonkeyPatch) -> None:
    from dda.utils.platform._pty.windows import PtySession

    class FakePty:
        def isalive(self) -> bool:
            return True

    session = PtySession.__new__(PtySession)
    cast(Any, session).pty = FakePty()
    writes: list[str] = []
    cast(Any, session)._write_stdin = writes.append

    fake_msvcrt = types.SimpleNamespace(
        kbhit=lambda: True,
        getwch=lambda: "\x03",
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    interrupted = False

    def fake_raise_signal(sig: int) -> None:
        nonlocal interrupted
        assert sig == signal.SIGINT
        interrupted = True

    monkeypatch.setattr(signal, "raise_signal", fake_raise_signal)

    session._forward_console_stdin(threading.Event())

    assert interrupted is True
    assert writes == []
