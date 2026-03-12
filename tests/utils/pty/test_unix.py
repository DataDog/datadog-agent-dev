# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import codecs
import io
import os
import sys
import threading

import pytest


@pytest.mark.skipif(sys.platform == "win32", reason="Unix only test")
def test_unix_session_closing_fd_stops_reader():
    from dda.utils.platform._pty.unix import PtySession

    session = PtySession.__new__(PtySession)
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
