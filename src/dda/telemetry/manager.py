# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.utils.fs import Path


class TelemetryManager:
    def __init__(self, app: Application) -> None:
        self.__app = app

        self.__started = False

    def submit_data(self, key: str, value: str) -> None:
        if not self.__enabled:
            return

        if not self.__started:
            self.__start_daemon()

        self.__write_dir.joinpath(key).write_text(value, encoding="utf-8")

    def consent(self) -> None:
        self.__consent_file.parent.ensure_dir()
        self.__consent_file.write_text("1", encoding="utf-8")

    def dissent(self) -> None:
        self.__consent_file.parent.ensure_dir()
        self.__consent_file.write_text("0", encoding="utf-8")

    def consent_recorded(self) -> bool:
        return self.__consent_file.is_file()

    def read_log(self) -> str:
        return self.__log_file.read_text(encoding="utf-8") if self.__log_file.is_file() else ""

    def clear_log(self) -> None:
        if self.__log_file.is_file():
            self.__log_file.unlink()

    @cached_property
    def __enabled(self) -> bool:
        return self.__consent_file.read_text(encoding="utf-8") == "1" if self.consent_recorded() else False

    @cached_property
    def __consent_file(self) -> Path:
        return self.__storage_dir / "consent.txt"

    @cached_property
    def __log_file(self) -> Path:
        return self.__storage_dir / "daemon.log"

    @cached_property
    def __storage_dir(self) -> Path:
        return self.__app.config.storage.cache / "telemetry"

    @cached_property
    def __write_dir(self) -> Path:
        from tempfile import mkdtemp

        from dda.utils.fs import Path

        return Path(mkdtemp(prefix="dda-telemetry-"))

    def __start_daemon(self) -> None:
        import sys

        from dda.utils.process import EnvVars

        env_vars = EnvVars({
            "DDA_TELEMETRY_WRITE_DIR": str(self.__write_dir),
            "DDA_TELEMETRY_LOG_FILE": str(self.__log_file),
        })
        self.__app.subprocess.spawn_daemon([sys.executable, "-m", "dda.telemetry.daemon"], env=env_vars)
        self.__started = True
