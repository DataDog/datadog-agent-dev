# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.tools.docker import Docker as DockerTool

if TYPE_CHECKING:
    from dda.env.models import EnvironmentStatus


class Docker(DockerTool):
    def get_status(self, container_name: str) -> EnvironmentStatus:
        import json

        from dda.env.models import EnvironmentState, EnvironmentStatus

        output = self.capture(["inspect", container_name], check=False)
        items = json.loads(output)
        if not items:
            return EnvironmentStatus(state=EnvironmentState.NONEXISTENT)

        inspection = items[0]

        # https://docs.docker.com/reference/api/engine/version/v1.47/#tag/Container/operation/ContainerList
        # https://docs.podman.io/en/latest/_static/api.html?version=v5.0#tag/containers-(compat)/operation/ContainerList
        state_data = inspection["State"]
        status = state_data["Status"].lower()
        if status == "running":
            state = EnvironmentState.STARTED
        elif status in {"created", "paused"}:
            state = EnvironmentState.STOPPED
        elif status == "exited":
            state = EnvironmentState.ERROR if state_data["ExitCode"] == 1 else EnvironmentState.STOPPED
        elif status == "restarting":
            state = EnvironmentState.STARTING
        elif status == "removing":
            state = EnvironmentState.STOPPING
        else:
            state = EnvironmentState.UNKNOWN

        return EnvironmentStatus(state=state)
