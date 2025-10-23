# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING, override

from msgspec import Struct

from dda.utils.fs import Path

if TYPE_CHECKING:
    from dda.cli.application import Application


class DigestType(StrEnum):
    """
    The type of digest for a build artifact, i.e. the possible values for the `digest` field in the BuildMetadata struct.
    """

    # Digest applicable to files
    # Suport only SHA256 for now
    FILE_SHA256 = auto()

    # Digest applicable to OCI container images
    # Use the OCI image digest format (result of `docker image inspect <image> --format '{{.Id}}'`)
    OCI_DIGEST = auto()

    # Other digest types - used for non-standard digest types
    OTHER = auto()

    @classmethod
    @override
    def _missing_(cls, value: object) -> DigestType:
        # TODO: Add a warning here probably
        return cls.OTHER

    def calculate_digest(self, app: Application, artifact_spec: Path | str) -> ArtifactDigest:
        match self:
            case DigestType.FILE_SHA256:
                digest_value = Path(artifact_spec).hexdigest(algorithm="sha256")
            case DigestType.OCI_DIGEST:
                digest_value = app.tools.docker.get_image_digest(str(artifact_spec))
            case _:
                msg = f"Cannot calculate digest for digest type: {self}"
                raise NotImplementedError(msg)

        return ArtifactDigest(value=digest_value, type=self)


class ArtifactDigest(Struct, frozen=True):
    """
    A digest for a build artifact.
    """

    value: str
    type: DigestType

    def __post_init__(self) -> None:
        # Validate the digest value for the given digest type
        match self.type:
            case DigestType.FILE_SHA256:
                check_valid_sha256_digest(self.value)
            case DigestType.OCI_DIGEST:
                if not self.value.startswith("sha256:"):
                    msg = f"OCI digest value must start with 'sha256:': {self.value}"
                    raise ValueError(msg)
                check_valid_sha256_digest(self.value.removeprefix("sha256:"))
            case DigestType.OTHER:
                # TODO: Maybe warning here
                pass
            case _:
                msg = f"Unsupported digest type: {self.type}"
                raise NotImplementedError(msg)


def check_valid_sha256_digest(digest: str) -> None:
    """
    Check if the digest is a valid SHA256 digest.
    """
    if not (all(x in "0123456789abcdef" for x in digest) and len(digest) == 64):  # noqa: PLR2004
        msg = f"Value is not a valid SHA256 digest: {digest}"
        raise ValueError(msg)
