# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Enable telemetry", hidden=True)
@pass_app
def cmd(app: Application) -> None:
    """
    Enable telemetry.
    """
    app.telemetry.consent()
