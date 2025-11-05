# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from dda.build.artifacts.binaries.base import BinaryArtifact

if TYPE_CHECKING:
    from dda.cli.application import Application


class CoreAgent(BinaryArtifact):
    """
    Build artifact for the `core-agent` binary.
    """

    @property
    @override
    def name(self) -> str:
        return "core-agent"

    def build(self, app: Application, *args: Any, **kwargs: Any) -> None:
        msg = "Not implemented"
        raise NotImplementedError(msg)
