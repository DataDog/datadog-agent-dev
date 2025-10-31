# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID  # noqa: TC003 - needed outside of typecheck for msgspec decode

from msgspec import Struct

from dda.build.metadata.digests import ArtifactDigest  # noqa: TC001 - needed outside of typecheck for msgspec decode
from dda.build.metadata.formats import ArtifactFormat, ArtifactType
from dda.build.metadata.platforms import OS, Arch, Platform
from dda.utils.fs import Path
from dda.utils.git.changeset import ChangeSet  # noqa: TC001 - needed outside of typecheck for msgspec decode
from dda.utils.git.commit import Commit  # noqa: TC001

if TYPE_CHECKING:
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
    def spawn_from_context(
        cls,
        context_data: _MetadataRequiredContext,
        artifact_digest: ArtifactDigest,
    ) -> BuildMetadata:
        """
        Create a BuildMetadata instance for the current build.
        Takes two arguments:
        - context_data: A _MetadataRequiredContext instance containing the required data to generate build metadata.
            This can be created with the `analyze_context` function.
        - artifact_digest: An ArtifactDigest instance containing the digest of the artifact.
            This can be calculated with the `DigestType.calculate_digest` method.
            For example, starting from the _MetadataRequiredContext instance, you can do:
            ```python
            context_details: _MetadataRequiredContext = analyze_context(ctx, app)
            artifact_digest = context_details.artifact_format.digest_type.calculate_digest(
                app, <path to the artifact or container image reference>
            )
            ```
        The _MetadataRequiredContext instance can have its fields overridden if the defaults obtained from the context are not correct.
        Returns:
            A fully initialized BuildMetadata instance. The `id` and `build_time` fields are automatically generated.
        """

        # Current time and ID
        build_time = datetime.now()  # noqa: DTZ005
        artifact_id = generate_build_id()

        return cls(
            id=artifact_id,
            build_time=build_time,
            digest=artifact_digest,
            **context_data.dump(),
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
        if self.worktree_diff.files:
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


def analyze_context(ctx: Context, app: Application) -> _MetadataRequiredContext:
    """
    Analyze the context to get the required data to generate build metadata.
    """
    return _MetadataRequiredContext.from_context(ctx, app)


class _MetadataRequiredContext(Struct):
    """
    Collection of fields obtained from build context to generate build metadata.
    Having this as a separate struct allows for easier overriding - this struct is explicitely not frozen.
    """

    agent_components: set[str]
    artifact_format: ArtifactFormat

    # Source tree fields
    commit: Commit
    worktree_diff: ChangeSet

    # Compatibility fields
    compatible_platforms: set[Platform]

    # Build metadata
    build_platform: Platform

    @classmethod
    def from_context(cls, ctx: Context, app: Application) -> _MetadataRequiredContext:
        """
        Create a _MetadataRequiredContext instance from the application and build context.
        Some values might not be correct for some artifacts, in which case they should be overridden afterwards.

        Defaults:
        - agent_components: Extracted from the calling command for DIST artifacts, or set to a single component for COMP artifacts.
        - artifact_format: Extracted from the calling command.
        - commit: The HEAD commit of the currently checked-out repo.
        - worktree_diff: The changes in the working tree compared to HEAD.
        - compatible_platforms: Defaults to a singleton of the build platform. This can be overridden to add more compatible platforms if possible.
        - build_platform: The platform this code is being run on.
        """

        import platform

        # Build components
        build_components = get_build_components(ctx.command_path)
        agent_components, artifact_format = build_components

        # Build platform
        build_platform = Platform.from_alias(platform.system().lower(), platform.machine())

        return cls(
            agent_components=agent_components,
            artifact_format=artifact_format,
            commit=app.tools.git.get_commit(),
            worktree_diff=app.tools.git.get_changes("HEAD", start="HEAD", working_tree=True),
            compatible_platforms={build_platform},
            build_platform=build_platform,
        )

    def dump(self) -> dict[str, Any]:
        """
        Dump the context data to a dictionary.
        """
        return {k: getattr(self, k) for k in self.__struct_fields__}
