# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import threading
import time

import pytest

from dda.utils.platform._pty.handle import ThreadedPtyIoHandle


def test_threaded_pty_io_handle_cancel_sets_stop_event():
    stop_event = threading.Event()
    cancelled = False

    def cancel_reader() -> None:
        nonlocal cancelled
        cancelled = True

    handle = ThreadedPtyIoHandle(
        lambda: None,
        stop_event=stop_event,
        cancel_reader=cancel_reader,
    )
    handle.cancel()

    assert stop_event.is_set() is True
    assert cancelled is True


def test_threaded_pty_io_handle_join_stops_input_thread():
    stop_event = threading.Event()

    def keep_running() -> None:
        while not stop_event.is_set():
            time.sleep(0.001)

    handle = ThreadedPtyIoHandle(
        lambda: None,
        stop_event=stop_event,
        stdin_target=keep_running,
    )
    handle.join()

    assert stop_event.is_set() is True


def test_threaded_pty_io_handle_join_stops_input_before_reader_finishes():
    stop_event = threading.Event()
    reader_released = threading.Event()
    stdin_stopped = threading.Event()

    def reader() -> None:
        reader_released.wait(timeout=1.0)

    def keep_running() -> None:
        while not stop_event.is_set():
            time.sleep(0.001)

        stdin_stopped.set()

    handle = ThreadedPtyIoHandle(
        reader,
        stop_event=stop_event,
        stdin_target=keep_running,
    )

    join_thread = threading.Thread(target=handle.join)
    join_thread.start()

    stdin_stopped.wait(timeout=1.0)
    assert stdin_stopped.is_set() is True
    assert join_thread.is_alive() is True

    reader_released.set()
    join_thread.join(timeout=1.0)

    assert not join_thread.is_alive()


def test_threaded_pty_io_handle_join_does_not_block_on_stuck_input_thread():
    stop_event = threading.Event()
    release_stdin = threading.Event()

    def stuck_input() -> None:
        release_stdin.wait()

    handle = ThreadedPtyIoHandle(
        lambda: None,
        stop_event=stop_event,
        stdin_target=stuck_input,
        stdin_join_timeout=0.01,
    )

    start = time.perf_counter()
    handle.join()
    elapsed = time.perf_counter() - start

    release_stdin.set()

    assert elapsed < 0.5
    assert stop_event.is_set() is True


def test_threaded_pty_io_handle_join_does_not_cancel_natural_reader_shutdown():
    stop_event = threading.Event()
    started = threading.Event()
    cancelled = False

    def reader() -> None:
        started.set()

    def cancel_reader() -> None:
        nonlocal cancelled
        cancelled = True

    handle = ThreadedPtyIoHandle(
        reader,
        stop_event=stop_event,
        cancel_reader=cancel_reader,
        reader_join_timeout=0.05,
    )
    assert started.wait(timeout=1.0) is True
    handle.join()

    assert cancelled is False
    assert stop_event.is_set() is True


def test_threaded_pty_io_handle_join_waits_for_cancelled_reader_to_exit():
    stop_event = threading.Event()
    finished = threading.Event()

    def reader() -> None:
        while not stop_event.is_set():
            time.sleep(0.001)

        finished.set()

    handle = ThreadedPtyIoHandle(
        reader,
        stop_event=stop_event,
        reader_join_timeout=0.0,
    )
    handle.cancel()
    handle.join()

    assert finished.is_set() is True


def test_threaded_pty_io_handle_cancelled_join_does_not_block_on_stuck_reader():
    stop_event = threading.Event()

    def reader() -> None:
        while True:
            time.sleep(0.001)

    handle = ThreadedPtyIoHandle(
        reader,
        stop_event=stop_event,
        reader_join_timeout=0.01,
    )
    handle.cancel()

    start = time.perf_counter()
    handle.join()
    elapsed = time.perf_counter() - start

    assert elapsed < 0.5
    assert stop_event.is_set() is True


def test_threaded_pty_io_handle_join_cancels_stuck_reader_after_grace_period():
    stop_event = threading.Event()
    release_reader = threading.Event()
    cancelled = False

    def reader() -> None:
        while not release_reader.is_set():
            time.sleep(0.001)

    def cancel_reader() -> None:
        nonlocal cancelled
        cancelled = True
        release_reader.set()

    handle = ThreadedPtyIoHandle(
        reader,
        stop_event=stop_event,
        cancel_reader=cancel_reader,
        reader_join_timeout=0.01,
    )
    handle.join()

    assert cancelled is True
    assert stop_event.is_set() is True


def test_threaded_pty_io_handle_join_raises_background_error():
    stop_event = threading.Event()
    message = "boom"

    def fail() -> None:
        raise RuntimeError(message)

    handle = ThreadedPtyIoHandle(
        fail,
        stop_event=stop_event,
    )

    with pytest.raises(RuntimeError, match="boom"):
        handle.join()

    assert stop_event.is_set() is True


def test_threaded_pty_io_handle_join_suppresses_error_after_cancel():
    stop_event = threading.Event()
    started = threading.Event()
    message = "cancelled"

    def fail_after_cancel() -> None:
        started.set()
        while not stop_event.is_set():
            time.sleep(0.001)

        raise RuntimeError(message)

    handle = ThreadedPtyIoHandle(
        fail_after_cancel,
        stop_event=stop_event,
    )
    started.wait(timeout=1.0)

    handle.cancel()
    handle.join()
