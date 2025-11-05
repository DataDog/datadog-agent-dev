# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Build the `core-agent` binary.")
@pass_app
def cmd(app: Application) -> None:
    from dda.build.artifacts.binaries.core_agent import CoreAgent

    artifact = CoreAgent()
    app.display_waiting("Building the `core-agent` binary...")
    artifact.build(app)
