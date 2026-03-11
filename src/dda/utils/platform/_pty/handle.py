# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class PtyIoHandle(ABC):
    @abstractmethod
    def cancel(self) -> None: ...

    @abstractmethod
    def join(self) -> None: ...


class ThreadedPtyIoHandle(PtyIoHandle):
    POST_CANCEL_JOIN_TIMEOUT = 0.2

    def __init__(
        self,
        reader_target: Callable[[], None],
        *,
        stop_event: threading.Event,
        stdin_target: Callable[[], None] | None = None,
        cancel_reader: Callable[[], None] | None = None,
        reader_join_timeout: float | None = None,
        stdin_join_timeout: float = 1.0,
    ) -> None:
        self._stop_event = stop_event
        self._cancel_reader = cancel_reader
        self._reader_join_timeout = reader_join_timeout
        self._stdin_join_timeout = stdin_join_timeout
        self._background_error: BaseException | None = None
        self._background_error_lock = threading.Lock()
        self._cancelled = False
        self._reader_thread = threading.Thread(target=self._run_target, args=(reader_target,), daemon=True)
        self._stdin_thread = (
            None
            if stdin_target is None
            else threading.Thread(target=self._run_target, args=(stdin_target,), daemon=True)
        )
        self._reader_thread.start()
        if self._stdin_thread is not None:
            self._stdin_thread.start()

    @property
    def stop_event(self) -> threading.Event:
        return self._stop_event

    def cancel(self) -> None:
        self._cancelled = True
        self._stop_event.set()
        if self._cancel_reader is not None:
            self._cancel_reader()

    def join(self) -> None:
        self._join_stdin_thread()
        self._join_reader_thread()
        self._raise_background_error()

    def _join_reader_thread(self) -> None:
        if not self._cancelled:
            # Let the reader drain naturally after process exit so we do not
            # truncate captured output by forcing cancellation too early. If the
            # read side wedges after the process has already exited, give it a
            # grace period and then cancel the read so teardown can complete.
            self._reader_thread.join(timeout=self._reader_join_timeout)
            if self._reader_thread.is_alive():
                self._cancel_reader_if_needed()
                self._reader_thread.join(timeout=self.POST_CANCEL_JOIN_TIMEOUT)
            return

        self._reader_thread.join(timeout=self._reader_join_timeout)
        if self._reader_thread.is_alive():
            self._cancel_reader_if_needed()
            self._reader_thread.join(timeout=self.POST_CANCEL_JOIN_TIMEOUT)

    def _join_stdin_thread(self) -> None:
        self._stop_event.set()
        if self._stdin_thread is None:
            return

        # Console input helpers can block in platform calls even after the stop
        # event is set. The stdin thread is daemonized and not required for
        # output correctness once teardown begins, so do not wait forever here.
        self._stdin_thread.join(timeout=self._stdin_join_timeout)

    def _run_target(self, target: Callable[[], None]) -> None:
        try:
            target()
        except Exception as error:  # noqa: BLE001
            with self._background_error_lock:
                if self._background_error is None:
                    self._background_error = error

            self._stop_event.set()
            with suppress(Exception):
                self._cancel_reader_if_needed()

    def _raise_background_error(self) -> None:
        if self._cancelled or self._background_error is None:
            return

        error = self._background_error
        self._background_error = None
        raise error.with_traceback(error.__traceback__)

    def _cancel_reader_if_needed(self) -> None:
        if self._cancel_reader is not None:
            self._cancel_reader()
