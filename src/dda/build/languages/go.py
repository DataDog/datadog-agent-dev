# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Any


class GoArtifact(ABC):
    """
    Base class for all Go artifacts.
    Any artifact class for an artifact built with the Go compiler should inherit from this class and implement its methods.
    """

    @abstractmethod
    def get_build_tags(self, *args: Any, **kwargs: Any) -> set[str]:
        """
        Get the build tags to pass to the Go compiler for the artifact.
        """

    @abstractmethod
    def get_gcflags(self, *args: Any, **kwargs: Any) -> list[str]:
        """
        Get the gcflags to pass to the Go compiler for the artifact.
        """

    @abstractmethod
    def get_ldflags(self, *args: Any, **kwargs: Any) -> list[str]:
        """
        Get the ldflags to pass to the Go compiler for the artifact.
        """
        return []

    @abstractmethod
    def get_build_env(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        """
        Get the build environment variables to pass to the Go compiler for the artifact.
        """
