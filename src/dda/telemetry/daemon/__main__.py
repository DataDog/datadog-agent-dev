# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import asyncio
import atexit
import json
import logging
import os
from contextlib import ExitStack
from typing import TYPE_CHECKING, Any

import psutil
import watchfiles

from dda.secrets.api import fetch_api_key, read_api_key, save_api_key
from dda.telemetry.constants import DaemonEnvVars
from dda.telemetry.daemon.handler import finalize_error
from dda.utils.fs import Path
from dda.utils.secrets.secrets import fetch_api_key, read_api_key, save_api_key

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from dda.telemetry.daemon.base import TelemetryClient

COMMAND_PID = int(os.environ[DaemonEnvVars.COMMAND_PID])
WRITE_DIR = Path(os.environ[DaemonEnvVars.WRITE_DIR])

atexit.register(finalize_error)


def get_client(id: str, **kwargs: Any) -> TelemetryClient:  # noqa: A002
    if id == "trace":
        from dda.telemetry.daemon.trace import TraceTelemetryClient

        return TraceTelemetryClient(**kwargs)

    if id == "log":
        from dda.telemetry.daemon.log import LogTelemetryClient

        return LogTelemetryClient(**kwargs)

    message = f"Unknown client ID: {id}"
    raise ValueError(message)


async def watch_events(stop_event: asyncio.Event) -> AsyncIterator[Path]:
    # Use as an ordered set
    existing_files = dict.fromkeys(os.listdir(WRITE_DIR))
    try:
        async for changes in watchfiles.awatch(
            WRITE_DIR,
            stop_event=stop_event,
            recursive=False,
            rust_timeout=0,
            watch_filter=lambda c, p: (
                # Only filter the final atomically written file
                c == watchfiles.Change.added
                and not (fn := os.path.basename(p)).startswith("tmp")
                # ... and ignore files that were created before watching
                and fn not in existing_files
            ),
        ):
            if existing_files:
                for filename in existing_files:
                    yield WRITE_DIR / filename

                existing_files.clear()

            for file_change in changes:
                _, full_path = file_change
                yield Path(full_path)
    except Exception:
        logging.exception("Error watching for changes")

    if existing_files:
        for filename in existing_files:
            yield WRITE_DIR / filename


async def process_changes(stop_event: asyncio.Event, **kwargs: Any) -> None:
    with ExitStack() as stack:
        clients: dict[str, TelemetryClient] = {}
        async for path in watch_events(stop_event):
            client_id = path.name.split("_")[0]
            if (client := clients.get(client_id)) is None:
                try:
                    client = get_client(client_id, **kwargs)
                    stack.enter_context(client)
                except Exception:
                    logging.exception("Failed to set up client: %s", client_id)
                    continue

                clients[client_id] = client

            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                logging.exception("Failed to parse file: %s", path)
                continue

            try:
                client.send(data)
            except Exception:
                logging.exception("Failed to send data to client: %s", client_id)


async def main() -> None:
    logging.debug("Getting API key from keyring")
    try:
        api_key = read_api_key()
    except Exception:
        logging.exception("Failed to read API key from keyring")
        return

    if not api_key:
        logging.warning("No API key found in keyring, fetching from Vault")

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

    stop_event = asyncio.Event()
    task = asyncio.create_task(process_changes(stop_event, api_key=api_key))

    try:
        process = psutil.Process(COMMAND_PID)
    except Exception:  # noqa: BLE001
        logging.debug("Command process not found, assuming command has finished")
    else:
        if process.create_time() < psutil.Process().create_time():
            logging.debug("Waiting for command to finish")
            await asyncio.to_thread(process.wait)
        else:
            logging.debug("Command PID reused, assuming command has finished")

    await asyncio.sleep(2)
    stop_event.set()
    await task


if __name__ == "__main__":
    asyncio.run(main())
