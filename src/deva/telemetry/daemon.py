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
from datadog_api_client.v1.api.events_api import EventsApi
from datadog_api_client.v1.model.event_create_request import EventCreateRequest
from msgspec import ValidationError, convert

from deva.telemetry.model import TelemetryData
from deva.utils.fs import Path
from deva.utils.platform import join_command_args

WRITE_DIR = Path(os.environ["DEVA_TELEMETRY_WRITE_DIR"])
LOG_FILE = Path(os.environ["DEVA_TELEMETRY_LOG_FILE"])

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logging.info("Telemetry daemon started")


def nano_to_seconds(nano: int) -> float:
    return nano / 1_000_000_000


def main() -> None:
    logging.info("Getting API key from keyring")
    api_key = keyring.get_password("deva", "telemetry_api_key")
    if not api_key:
        logging.error("No API key found in keyring, fetching from Vault")

        from deva.telemetry.vault import fetch_secret

        try:
            api_key = fetch_secret("group/subproduct-agent/deva", "telemetry-api-key")
        except Exception:
            logging.exception("Failed to fetch API key from Vault")
            return

        logging.info("Storing API key in keyring")
        keyring.set_password("deva", "telemetry_api_key", api_key)

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

    body = EventCreateRequest(
        title="Deva command invoked",
        text=f"""\
Command: {command}
Exit code: {telemetry_data.exit_code}
Duration: {elapsed_time:.2f} seconds
""",
        tags=["cli:deva"],
    )
    config = Configuration(api_key={"apiKeyAuth": api_key})
    with ApiClient(config) as api_client:
        api_instance = EventsApi(api_client)
        api_instance.create_event(body=body)


if __name__ == "__main__":
    main()
