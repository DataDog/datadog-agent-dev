# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from dda.build.metadata.metadata import BuildMetadata, analyze_context

if TYPE_CHECKING:
    from typing import Any

    from dda.build.metadata.digests import ArtifactDigest
    from dda.build.metadata.formats import ArtifactFormat
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

    @abstractmethod
    def get_build_components(self) -> tuple[set[str], ArtifactFormat]:
        """
        Gets the build components and artifact format for this artifact.

        Returns:
            A tuple containing the build components and artifact format for this artifact.
        """

    def compute_metadata(self, app: Application, artifact_digest: ArtifactDigest) -> BuildMetadata:
        """
        Creates a BuildMetadata instance for this artifact.
        """
        from dda.build.metadata.metadata import BuildMetadata

        return BuildMetadata.spawn_from_context(analyze_context(app), self.get_build_components(), artifact_digest)
