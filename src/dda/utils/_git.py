# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os

GIT_AUTHOR_NAME_ENV_VAR = "GIT_AUTHOR_NAME"
GIT_AUTHOR_EMAIL_ENV_VAR = "GIT_AUTHOR_EMAIL"


def get_git_author_name() -> str:
    name = os.environ.get(GIT_AUTHOR_NAME_ENV_VAR)
    if name:
        return name

    import subprocess

    try:
        return subprocess.run(
            ["git", "config", "--global", "--get", "user.name"],  # noqa: S607
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def get_git_author_email() -> str:
    email = os.environ.get(GIT_AUTHOR_EMAIL_ENV_VAR)
    if email:
        return email

    import subprocess

    try:
        return subprocess.run(
            ["git", "config", "--global", "--get", "user.email"],  # noqa: S607
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""
