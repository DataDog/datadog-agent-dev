# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import codecs
import io
import os
import sys
import threading
import time
from typing import Any, cast

import pytest


def _unix_pty_session_type() -> Any:
    from dda.utils.platform._pty import unix

    return cast(Any, unix).PtySession


@pytest.mark.skipif(sys.platform == "win32", reason="Unix only test")
def test_unix_session_closing_fd_stops_reader():
    pty_session_type = _unix_pty_session_type()

    session = pty_session_type.__new__(pty_session_type)
    session._fd, writer_fd = os.pipe()
    session._fd_lock = threading.Lock()
    session.READ_INTERVAL_SECONDS = 0.01
    session.decoder = codecs.getincrementaldecoder("utf-8")()

    live_writer = io.StringIO()
    capture_writer = io.StringIO()
    thread = threading.Thread(target=session._drain_output, args=(live_writer, capture_writer), daemon=True)
    thread.start()

    session._close_fd()
    thread.join(timeout=1.0)

    os.close(writer_fd)

    assert not thread.is_alive()
    assert session._get_fd() is None


@pytest.mark.skipif(sys.platform == "win32", reason="Unix only test")
def test_unix_session_join_cancels_stuck_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    from dda.utils.platform._pty.handle import ThreadedPtyIoHandle

    pty_session_type = _unix_pty_session_type()

    session = pty_session_type.__new__(pty_session_type)
    session._fd, writer_fd = os.pipe()
    session._fd_lock = threading.Lock()
    session.READ_INTERVAL_SECONDS = 0.01
    session.decoder = codecs.getincrementaldecoder("utf-8")()

    monkeypatch.setattr(ThreadedPtyIoHandle, "POST_CANCEL_JOIN_TIMEOUT", 0.05)

    handle = session.start_io(io.StringIO(), io.StringIO())
    cast(Any, handle)._reader_join_timeout = 0.01

    try:
        start = time.perf_counter()
        handle.join()
        elapsed = time.perf_counter() - start
    finally:
        os.close(writer_fd)

    assert elapsed < 0.5
    assert cast(Any, handle)._reader_thread.is_alive() is False
    assert session._get_fd() is None
