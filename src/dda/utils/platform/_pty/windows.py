# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING

import winpty

from dda.utils.platform import join_command_args
from dda.utils.platform._pty.handle import ThreadedPtyIoHandle
from dda.utils.platform._pty.interface import PtySessionInterface
from dda.utils.platform._pty.windows_vt import WindowsVtShim, WinPtyAdapter
from dda.utils.terminal import terminal_size

# https://github.com/python/mypy/issues/19013
assert sys.platform == "win32"  # noqa: S101

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from dda.utils.fs import Path
    from dda.utils.platform._pty.handle import PtyIoHandle
    from dda.utils.platform._pty.interface import TextReader, TextWriter

WINDOWS_PTY_EXIT_CLEANUP = (
    # A terminal normally preserves active modes/styles until later output
    # explicitly resets them. Because we relay an inner PTY session into the
    # user's existing terminal, restore the most important state on teardown in
    # case the child exits before emitting the matching reset/disable codes.
    #
    # SGR reset
    "\x1b[0m"
    # Show cursor
    "\x1b[?25h"
    # Disable focus reporting
    "\x1b[?1004l"
    # Disable bracketed paste
    "\x1b[?2004l"
    # Disable Win32 Input Mode enabled by OpenConsole/pywinpty
    "\x1b[?9001l"
)


class PtySession(PtySessionInterface):
    def __init__(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None,
        cwd: str | Path | None,
        # TODO: Use this once it does something
        # https://github.com/andfoy/pywinpty/issues/510
        encoding: str,
    ) -> None:
        super().__init__(command, env=env, cwd=cwd, encoding=encoding)

        width, height = terminal_size()
        self.pty = WinPtyAdapter(winpty.PTY(width, height))
        self._vt_shim = WindowsVtShim()
        self.pty.spawn(
            # Add quotes if the executable path contains spaces
            join_command_args([self.executable]),
            cmdline=join_command_args(self.args) if self.args else None,
            cwd=self.cwd,
            env=(
                None
                if self.env is None
                else "\0".join([
                    *(f"{key}={value}" for key, value in self.env.items()),
                    "",
                ])
            ),
        )

    def start_io(
        self,
        live_writer: TextWriter,
        capture_writer: TextWriter,
        *,
        stdin_reader: TextReader | None = None,
    ) -> PtyIoHandle:
        stop_event = threading.Event()
        stdin_target = self._get_stdin_target(stdin_reader, stop_event)

        return ThreadedPtyIoHandle(
            lambda: self._drain_output(live_writer, capture_writer),
            stop_event=stop_event,
            stdin_target=stdin_target,
            cancel_reader=self._cancel_io,
            reader_join_timeout=1.0,
        )

    def _drain_output(self, live_writer: TextWriter, capture_writer: TextWriter) -> None:
        try:
            self._drain_output_body(live_writer, capture_writer)
        finally:
            self._write_output(live_writer, capture_writer, self._vt_shim.finish())
            capture_writer.flush()

    def _drain_output_body(self, live_writer: TextWriter, capture_writer: TextWriter) -> None:
        while True:
            try:
                output = self.pty.read()
            except winpty.WinptyError:
                if self.pty.iseof() or not self.pty.isalive():
                    break

                time.sleep(self.READ_INTERVAL_SECONDS)
                continue

            if not output:
                if self.pty.iseof() or not self.pty.isalive():
                    break

                time.sleep(self.READ_INTERVAL_SECONDS)
                continue

            output, replies = self._vt_shim.process(output)
            self._write_replies(replies)
            self._write_output(live_writer, capture_writer, output)

    def wait(self) -> None:
        while self.pty.get_exitstatus() is None:
            time.sleep(0.1)

    def terminate(self) -> None:
        import signal

        pid = self.pty.pid
        if pid is not None:
            os.kill(pid, signal.SIGTERM)

    def get_exit_code(self) -> int | None:
        return self.pty.get_exitstatus()

    def _cancel_io(self) -> None:
        with suppress(winpty.WinptyError):
            self.pty.cancel_io()

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        # https://github.com/andfoy/pywinpty/issues/484
        del self.pty

        print(WINDOWS_PTY_EXIT_CLEANUP)  # noqa: T201

    @staticmethod
    def _write_output(live_writer: TextWriter, capture_writer: TextWriter, output: str) -> None:
        if not output:
            return

        live_writer.write(output)
        live_writer.flush()
        capture_writer.write(output)

    def _write_replies(self, replies: tuple[str, ...]) -> None:
        for reply in replies:
            try:
                self.pty.write(reply)
            except winpty.WinptyError:
                return

    def _get_stdin_target(
        self, stdin_reader: TextReader | None, stop_event: threading.Event
    ) -> Callable[[], None] | None:
        if stdin_reader is None:
            return None

        return lambda: self._forward_stdin(stdin_reader, stop_event)

    def _forward_stdin(self, stdin_reader: TextReader, stop_event: threading.Event) -> None:
        if stdin_reader in {sys.stdin, sys.__stdin__}:
            self._forward_console_stdin(stop_event)
            return

        while not stop_event.is_set() and self.pty.isalive():
            data = stdin_reader.read(1)
            if not data:
                break

            self._write_stdin(data)

    def _forward_console_stdin(self, stop_event: threading.Event) -> None:
        import msvcrt
        import signal

        while not stop_event.is_set() and self.pty.isalive():
            if not msvcrt.kbhit():
                time.sleep(self.READ_INTERVAL_SECONDS)
                continue

            data = msvcrt.getwch()
            if data in {"\x00", "\xe0"}:
                data += msvcrt.getwch()
            elif data == "\x03":
                stop_event.set()
                signal.raise_signal(signal.SIGINT)
                return

            self._write_stdin(data)

    def _write_stdin(self, data: str) -> None:
        with suppress(winpty.WinptyError):
            self.pty.write(data)
