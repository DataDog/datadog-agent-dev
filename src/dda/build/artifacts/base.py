# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from dda.cli.application import Application


# NOTE: Very much speculative - this API might be subject to signficant changes !
class BuildArtifact(ABC):
    """
    Base class for all build artifacts.
    """

    @abstractmethod
    def build(self, app: Application, *args: Any, **kwargs: Any) -> None:
        """
        Build the artifact. This function can have arbitrary side effects (creating files, running commands, etc.), and is not expected to return anything.
        """
