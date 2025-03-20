# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
import os
import time
from ast import literal_eval

import keyring
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem
from msgspec import ValidationError, convert

from dda.telemetry.model import TelemetryData
from dda.utils.fs import Path
from dda.utils.platform import join_command_args

WRITE_DIR = Path(os.environ["DDA_TELEMETRY_WRITE_DIR"])
LOG_FILE = Path(os.environ["DDA_TELEMETRY_LOG_FILE"])

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logging.info("Telemetry daemon started")


def get_log_level(exit_code: int) -> str:
    if exit_code == 0:
        return "info"

    if 1 < exit_code < 128:  # noqa: PLR2004
        return "warn"

    return "error"


def nano_to_seconds(nano: int) -> float:
    return nano / 1_000_000_000


def main() -> None:
    logging.info("Getting API key from keyring")
    api_key = keyring.get_password("dda", "telemetry_api_key")
    if not api_key:
        logging.error("No API key found in keyring, fetching from Vault")

        from dda.telemetry.vault import fetch_secret

        try:
            # TODO: update this to the new secret path
            api_key = fetch_secret("group/subproduct-agent/deva", "telemetry-api-key")
        except Exception:
            logging.exception("Failed to fetch API key from Vault")
            return

        logging.info("Storing API key in keyring")
        keyring.set_password("dda", "telemetry_api_key", api_key)

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
            exit_code=telemetry_data.exit_code,
            duration=elapsed_time,
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
