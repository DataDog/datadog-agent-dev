# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Update internal Bazelisk")
@pass_app
def cmd(app: Application) -> None:
    """
    Update the internal Bazelisk binary.
    """
    if not app.tools.bazel.managed:
        app.abort(f"Bazel is not managed, using external version: {app.tools.bazel.path}")

    app.tools.bazel.update()
