# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
import os
import time
from ast import literal_eval

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem
from msgspec import ValidationError, convert

from dda.telemetry.constants import DaemonEnvVars
from dda.telemetry.model import TelemetryData
from dda.telemetry.secrets import fetch_api_key, read_api_key, save_api_key
from dda.utils.fs import Path
from dda.utils.platform import join_command_args

WRITE_DIR = Path(os.environ[DaemonEnvVars.WRITE_DIR])
LOG_FILE = Path(os.environ[DaemonEnvVars.LOG_FILE])

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logging.info("Telemetry daemon started")


def get_log_level(exit_code: int) -> str:
    if exit_code == 0:
        return "info"

    # https://github.com/pallets/click/blob/8.1.8/src/click/exceptions.py#L64
    if exit_code == 2:  # noqa: PLR2004
        return "warn"

    return "error"


def nano_to_seconds(nano: int) -> float:
    return nano / 1_000_000_000


def main() -> None:
    logging.info("Getting API key from keyring")
    try:
        api_key = read_api_key()
    except Exception:
        logging.exception("Failed to read API key from keyring")
        return

    if not api_key:
        logging.error("No API key found in keyring, fetching from Vault")

        try:
            api_key = fetch_api_key()
        except Exception:
            logging.exception("Failed to fetch API key from Vault")
            return

        logging.info("Storing API key in keyring")
        try:
            save_api_key(api_key)
        except Exception:
            logging.exception("Failed to save API key to keyring")

    while True:
        data = {}
        for path in WRITE_DIR.iterdir():
            key = path.name
            value = path.read_text(encoding="utf-8").strip()
            data[key] = value

        try:
            telemetry_data = convert(data, TelemetryData, strict=False)
        except ValidationError:
            logging.exception("Failed to convert telemetry data")
            time.sleep(5)
            continue

        logging.info("Received telemetry data: %s", telemetry_data)
        break

    command = join_command_args(literal_eval(telemetry_data.command))
    elapsed_time = nano_to_seconds(telemetry_data.end_time - telemetry_data.start_time)

    logging.info("Creating HTTPLogItem")
    try:
        log_item = HTTPLogItem(
            message=f"{command} (exit code: {telemetry_data.exit_code}, duration: {elapsed_time:.2f} seconds)",
            level=get_log_level(telemetry_data.exit_code),
            service="cli-dda",
            ddtags="cli:dda",
            exit_code=str(telemetry_data.exit_code),
            duration=str(elapsed_time),
        )
    except Exception:
        logging.exception("Failed to create HTTPLogItem")
        return

    logging.info("Submitting HTTPLog")
    config = Configuration(api_key={"apiKeyAuth": api_key})
    with ApiClient(config) as api_client:
        api_instance = LogsApi(api_client)
        api_instance.submit_log(body=HTTPLog(value=[log_item]))

    logging.info("Submitted log item: %s", log_item)


if __name__ == "__main__":
    main()
