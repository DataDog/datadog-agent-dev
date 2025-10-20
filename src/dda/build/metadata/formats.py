# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from enum import StrEnum, auto

from msgspec import Struct


class ArtifactFormat(StrEnum):
    """
    Enum of all available artifact formats.
    """

    # Distribution formats
    DEB = auto()
    RPM = auto()
    MSI = auto()
    OCI = auto()

    # Component formats
    BIN = auto()

    # Properties for the underlying format details
    @property
    def type(self) -> ArtifactType:
        return _ARTIFACT_FORMAT_DETAILS[self.name].artifact_type

    def get_file_identifier(self) -> str:
        return _ARTIFACT_FORMAT_DETAILS[self.name].file_identifier


class ArtifactType(StrEnum):
    """
    The type of a build artifact: either a "component" or a "distribution".
    Each artifact type has a corresponding format enum.
    """

    COMP = auto()
    DIST = auto()


class _ArtifactFormatDetails(Struct, frozen=True):
    """
    Details of an artifact format.
    This implementation (with a string indexing a dict of details) is used to workaround msgspec's encoding logic for Enums, which cannot handle complex objects.
    All valid formats are registered in the ArtifactFormat enum.
    """

    file_identifier: str
    artifact_type: ArtifactType


_ARTIFACT_FORMAT_DETAILS: dict[str, _ArtifactFormatDetails] = {
    "DEB": _ArtifactFormatDetails(file_identifier=".deb", artifact_type=ArtifactType.DIST),
    "RPM": _ArtifactFormatDetails(file_identifier=".rpm", artifact_type=ArtifactType.DIST),
    "MSI": _ArtifactFormatDetails(file_identifier=".msi", artifact_type=ArtifactType.DIST),
    "OCI": _ArtifactFormatDetails(file_identifier="-oci.tar.gz", artifact_type=ArtifactType.DIST),
    "BIN": _ArtifactFormatDetails(file_identifier="", artifact_type=ArtifactType.COMP),
}

# Validate that the keys of the _ArtifactFormatDetails dict match the keys of the ArtifactFormat enum
# Better to do this here than as a test
if _ARTIFACT_FORMAT_DETAILS.keys() != ArtifactFormat.__members__.keys():
    msg = "ArtifactFormat and _ArtifactFormatDetails keys do not match"
    raise ValueError(msg)
