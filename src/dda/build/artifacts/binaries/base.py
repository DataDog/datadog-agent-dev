# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.build.artifacts.base import BuildArtifact


class BinaryArtifact(BuildArtifact):
    """
    Base class for all binary build artifacts.
    """
