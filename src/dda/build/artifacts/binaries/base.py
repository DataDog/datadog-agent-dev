# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, override

from dda.build.artifacts.base import BuildArtifact

if TYPE_CHECKING:
    from dda.build.metadata.formats import ArtifactFormat


class BinaryArtifact(BuildArtifact):
    """
    Base class for all binary build artifacts.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of the binary artifact this object represents.
        """

    @override
    def get_build_components(self) -> tuple[set[str], ArtifactFormat]:
        from dda.build.metadata.formats import ArtifactFormat

        return {self.name}, ArtifactFormat.BIN
