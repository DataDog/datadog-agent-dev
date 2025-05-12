# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.telemetry.writers.log import LogTelemetryWriter
    from dda.telemetry.writers.trace import TraceTelemetryWriter
    from dda.utils.fs import Path


class TelemetryManager:
    """
    A class for sending various forms of telemetry. This is available as the
    [`Application.telemetry`][dda.cli.application.Application.telemetry] property.
    """

    def __init__(self, app: Application) -> None:
        self.__app = app

        self.__started = False

    @property
    def enabled(self) -> bool:
        """
        Whether the user has consented to telemetry.
        """
        return self.__enabled

    @cached_property
    def log(self) -> LogTelemetryWriter:
        from dda.telemetry.writers.log import LogTelemetryWriter

        return LogTelemetryWriter(path=self.__write_dir, enabled=self.__enabled)

    @cached_property
    def trace(self) -> TraceTelemetryWriter:
        from dda.telemetry.writers.trace import TraceTelemetryWriter

        return TraceTelemetryWriter(path=self.__write_dir, enabled=self.__enabled)

    def watch(self) -> None:
        if self.__enabled and not self.__started:
            self.__start_daemon()

    def consent(self) -> None:
        self.__consent_file.parent.ensure_dir()
        self.__consent_file.write_text("1", encoding="utf-8")

    def dissent(self) -> None:
        self.__consent_file.parent.ensure_dir()
        self.__consent_file.write_text("0", encoding="utf-8")

    def consent_recorded(self) -> bool:
        return self.__consent_file.is_file()

    def clear_log(self) -> None:
        if self.log_file.is_file():
            self.log_file.unlink()

    @cached_property
    def log_file(self) -> Path:
        return self.__storage_dir / "daemon.log"

    @cached_property
    def api_key(self) -> str | None:
        if not self.__enabled:
            return None

        from contextlib import suppress

        from dda.telemetry.secrets import fetch_api_key, read_api_key, save_api_key

        api_key: str | None = None
        with suppress(Exception):
            api_key = read_api_key()
            if not api_key:
                api_key = fetch_api_key()
                save_api_key(api_key)

        return api_key

    @cached_property
    def __enabled(self) -> bool:
        return self.__consent_file.read_text(encoding="utf-8") == "1" if self.consent_recorded() else False

    @cached_property
    def __consent_file(self) -> Path:
        return self.__storage_dir / "consent.txt"

    @cached_property
    def __storage_dir(self) -> Path:
        return self.__app.config.storage.cache / "telemetry"

    @cached_property
    def __write_dir(self) -> Path:
        from tempfile import mkdtemp

        from dda.utils.fs import Path

        return Path(mkdtemp(prefix="dda-telemetry-"))

    def __start_daemon(self) -> None:
        import os
        import sys

        from dda.telemetry.constants import DaemonEnvVars
        from dda.utils.process import EnvVars

        env_vars = EnvVars({
            DaemonEnvVars.COMMAND_PID: str(os.getpid()),
            DaemonEnvVars.WRITE_DIR: str(self.__write_dir),
            DaemonEnvVars.LOG_FILE: str(self.log_file),
        })
        self.__app.subprocess.spawn_daemon([sys.executable, "-m", "dda.telemetry.daemon"], env=env_vars)
        self.__started = True
