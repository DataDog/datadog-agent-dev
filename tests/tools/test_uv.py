# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import threading
import time


def test_virtual_env_serializes_concurrent_creation(app, temp_dir, mocker):
    """
    Concurrent callers targeting the same, not-yet-created virtual environment path must serialize
    creation: `uv venv` errors if the target already exists by the time it runs.
    """
    venv_path = temp_dir / "venv"
    call_count = 0
    call_count_lock = threading.Lock()

    def fake_wait(command, **kwargs):  # noqa: ARG001
        nonlocal call_count
        with call_count_lock:
            call_count += 1
        # Simulate `uv venv` taking long enough for other threads to still see the directory missing.
        time.sleep(0.2)
        venv_path.mkdir(parents=True, exist_ok=True)
        return 0

    mocker.patch("dda.tools.base.Tool.wait", side_effect=fake_wait)

    errors: list[Exception] = []

    def worker():
        try:
            app.tools.uv.virtual_env(venv_path)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert call_count == 1
