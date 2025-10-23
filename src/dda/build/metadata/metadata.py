# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - needed outside of typecheck for msgspec decode

from msgspec import Struct

from dda.build.metadata.enums import OS, Arch, DigestType, Platform
from dda.build.metadata.formats import ArtifactFormat, ArtifactType
from dda.utils.fs import Path
from dda.utils.git.changeset import ChangeSet  # noqa: TC001 - needed outside of typecheck for msgspec decode
from dda.utils.git.commit import Commit  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Iterable

    from click import Context

    from dda.cli.application import Application


class BuildMetadata(Struct, frozen=True):
    """
    Metadata about a build that can be used to identify it.
    """

    # Basic fields
    id: UUID
    agent_components: set[str]
    artifact_format: ArtifactFormat

    # Source tree fields
    commit: Commit
    worktree_diff: ChangeSet

    # Compatibility fields
    compatible_platforms: set[Platform]

    # Build metadata
    build_platform: Platform
    build_time: datetime

    # Artifact-related fields
    digest: ArtifactDigest

    def __post_init__(self) -> None:
        if self.artifact_type == ArtifactType.COMP and len(self.agent_components) != 1:
            msg = "An agent component artifact can only represent a single component"
            raise ValueError(msg)

        os_set = {platform.os for platform in self.compatible_platforms}
        arch_set = {platform.arch for platform in self.compatible_platforms}
        if OS.ANY in os_set and len(os_set) > 1:
            msg = "Cannot use both the 'any' OS and other OSs in compatible platforms"
            raise ValueError(msg)
        if Arch.ANY in arch_set and len(arch_set) > 1:
            msg = "Cannot have both any architecture and other architectures in compatible platforms"
            raise ValueError(msg)

    @property
    def artifact_type(self) -> ArtifactType:
        """The artifact type."""
        return self.artifact_format.type

    @classmethod
    def this(
        cls,
        ctx: Context,
        app: Application,
        artifact: Path | str,
        *,
        build_components: tuple[set[str], ArtifactFormat] | None = None,
        compatible_platforms: Iterable[Platform] | None = None,
    ) -> BuildMetadata:
        """
        Create a BuildMetadata instance for the current build.
        Most arguments are inferred from context:
            - A UUID is generated
            - Build time is automatically set to the current time
            - Source info (commit hash and worktree diff) are computed from the current git checkout
            ...

        The set of agent components is extracted from the current called command, but can be overriden by the `build_components` argument.
        The compatible platforms are set to the build platform if not provided, but can be overriden by the `compatible_platforms` argument.

        Args:
            build_components: A tuple containing the agent components, artifact type, and artifact format for override.
                If not provided, they will be extracted from the calling command via the `get_build_components` function.
            compatible_platforms: An optional iterable of platforms to indicate the platform compatibility of the build.
                If not provided, the build platform will be used as sole compatible platform.
        """
        import platform

        # Current time and ID
        build_time = datetime.now()  # noqa: DTZ005
        artifact_id = generate_build_id()

        # Build components
        if build_components is None:
            build_components = get_build_components(ctx.command_path)
        agent_components, artifact_format = build_components

        # Build platform
        build_platform = Platform.from_alias(platform.system().lower(), platform.machine())
        compatible_platforms = compatible_platforms or {build_platform}

        # Get worktree information - base commit and diff hash
        worktree_diff = app.tools.git.get_changes("HEAD", start="HEAD", working_tree=True)
        commit = app.tools.git.get_commit()

        # Calculate digest
        digest_type = artifact_format.digest_type
        match digest_type:
            case DigestType.FILE_SHA256:
                digest_value = Path(artifact).hexdigest(algorithm="sha256")
            case DigestType.OCI_DIGEST:
                digest_value = app.tools.docker.get_image_digest(str(artifact))
            case _:
                msg = f"Unsupported digest type: {digest_type}"
                raise NotImplementedError(msg)

        return cls(
            id=artifact_id,
            agent_components=agent_components,
            artifact_format=artifact_format,
            commit=commit,
            compatible_platforms=set(compatible_platforms),
            build_platform=build_platform,
            build_time=build_time,
            worktree_diff=worktree_diff,
            digest=ArtifactDigest(value=digest_value, type=digest_type),
        )

    def to_file(self, path: Path | None = None) -> None:
        """
        Write the build metadata to a file.
        """
        from msgspec.json import encode

        from dda.types.hooks import enc_hook

        if path is None:
            path = Path(f"{self.get_canonical_filename()}.json")

        path.write_atomic(encode(self, enc_hook=enc_hook), "wb")

    @classmethod
    def from_file(cls, path: Path) -> BuildMetadata:
        """
        Read the build metadata from a file.
        """
        from msgspec.json import decode

        from dda.types.hooks import dec_hook

        return decode(path.read_text(encoding="utf-8"), type=cls, dec_hook=dec_hook)

    def get_canonical_filename(self) -> str:
        """
        Get a predictable filename corresponding to the artifact represented by this metadata.
        Schema is: `{components}-{compatibility}-{source info}-{short uuid}-{artifact format identifier}`.
        Where:
        - `components` is the name of the agent component.
            For components named `x-agent`, we will use `x` instead, omitting the `-agent` suffix.
            Any `-` characters will be replaced with `_`.
            If there are multiple components, a comma-separated list will be used, sorted alphabetically.
        - `compatibility` is a platform identifier, e.g. `linux-arm64`.
            If there are multiple compatible platforms, the string `many` will be used instead.
            If the platform compatibility is `any, any`, the string `any` will be used instead.
        - `source_info` is the short commit SHA, appended with `+{worktree diff hash}` if there are any working tree changes.
        - `short uuid` is the first section of the UUID attributed to the artifact.
        - `artifact_format_identifier` gives info on the contents of the artifact when it is a dist. See `ArtifactFormat.get_file_identifier` for more details.
        NOTE: For binaries, we do not use `.bin`, instead leaving the file extension blank.

        Returns:
            A predictable filename corresponding to the artifact represented by this metadata.
        """
        # TODO: Discuss this schema in a document, this is a first idea

        # Components
        components = ",".join(
            sorted(component.replace("-agent", "").replace("-", "_") for component in self.agent_components)
        )

        # Short UUID
        short_uuid = self.id.urn.split(":")[2].split("-")[0]

        # Source info
        source_info = self.commit.sha1[:8]
        if self.worktree_diff:
            source_info += f"+{self.worktree_diff.digest()[:8]}"

        # Compatibility
        if Platform.ANY in self.compatible_platforms:
            compatibility = "any"
        elif len(self.compatible_platforms) > 1:
            compatibility = "many"
        else:
            # Also handles the case in which os is `any` or `arch` is `any`
            platform = self.compatible_platforms.copy().pop()
            compatibility = str(platform)

        # Artifact format identifier
        artifact_format_identifier = self.artifact_format.get_file_identifier()
        return f"{components}-{compatibility}-{source_info}-{short_uuid}{artifact_format_identifier}"


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


def get_build_components(command: str) -> tuple[set[str], ArtifactFormat]:
    """
    Parse calling command to get the agent components and artifact format.

    Ex:
        `dda build comp core-agent` -> (`core-agent`), `comp` and `bin`
        `dda build dist deb -c core-agent -c process-agent` -> (`core-agent`, `process-agent`), `dist` and `deb`
    """
    command_parts = command.split(" ")
    # Remove the first two parts, which are `dda` and `build`, if they exist
    if command_parts[:2] != ["dda", "build"]:
        msg = f"Unexpected command, only build commands can be used to extract build components: {command}"
        raise ValueError(msg)

    artifact_format: ArtifactFormat
    artifact_type_str = command_parts[2]
    match artifact_type_str:
        case "dist":
            artifact_format = ArtifactFormat[command_parts[3].upper()]
            # TODO: Implement this in a more robust way, write a proper parser for the command line
            agent_components = {part for part in command_parts[4:] if part != "-c"}
        case "comp":
            # TODO: support other component formats for comps - default to bin for now
            artifact_format = ArtifactFormat.BIN
            agent_components = {command_parts[3]}
        case _:
            msg = f"Unsupported artifact type: {artifact_type_str}"
            raise NotImplementedError(msg)

    return agent_components, artifact_format


def generate_build_id() -> UUID:
    """
    Generate a unique build ID.
    """
    from uuid import uuid4

    return uuid4()
