# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from msgspec import Struct

from dda.build.metadata.enums import OS, Arch, ArtifactFormat, ArtifactType, Platform
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
    id: int
    agent_components: set[str]
    artifact_type: ArtifactType
    artifact_format: ArtifactFormat

    # Source tree fields
    commit: Commit
    worktree_diff: ChangeSet

    # Compatibility fields
    compatible_platforms: set[Platform]

    # Build metadata
    build_platform: Platform
    build_time: datetime

    def __post_init__(self) -> None:
        self.artifact_format.validate_for_type(self.artifact_type)

    @classmethod
    def this(
        cls, ctx: Context, app: Application, *, compatible_platforms: Iterable[Platform] | None = None
    ) -> BuildMetadata:
        """
        Create a BuildMetadata instance for the current build.
        """
        import platform

        # Current time and ID
        build_time = datetime.now()  # noqa: DTZ005
        artifact_id = generate_build_id()

        # Parse calling command to get the agent components, artifact type, and artifact format
        # e.g. `dda build comp core-agent` -> (`core-agent`), `comp` and `bin`
        # e.g. `dda build dist deb -c core-agent -c process-agent` -> (`core-agent`, `process-agent`), `dist` and `deb`
        command_parts = ctx.command_path.split(" ")
        if command_parts[1] != "build":
            msg = f"Unexpected command path, BuildMetadata.this can only be called from within: {ctx.command_path}"
            raise ValueError(msg)

        artifact_type = ArtifactType(command_parts[2])
        match artifact_type:
            case ArtifactType.DIST:
                artifact_format = ArtifactFormat(command_parts[3])
                # TODO: Implement this in a more robust way, write a proper parser for the command line
                agent_components = {part for part in command_parts[4:] if part != "-c"}
            case ArtifactType.COMP:
                # TODO: support other component formats for comps - default to bin for now
                artifact_format = ArtifactFormat.BIN
                agent_components = {command_parts[3]}
            case _:
                msg = f"Unsupported artifact type: {artifact_type}"
                raise NotImplementedError(msg)

        # Build platform
        build_platform = OS.from_alias(platform.system().lower()), Arch.from_alias(platform.machine())
        compatible_platforms = compatible_platforms or {build_platform}

        # Get worktree information - base commit and diff hash
        worktree_diff = app.tools.git.get_changes("HEAD", start="HEAD", working_tree=True)
        commit = app.tools.git.get_commit()

        return cls(
            id=artifact_id,
            agent_components=agent_components,
            artifact_format=artifact_format,
            artifact_type=artifact_type,
            commit=commit,
            compatible_platforms=set(compatible_platforms),
            build_platform=build_platform,
            build_time=build_time,
            worktree_diff=worktree_diff,
        )


def generate_build_id() -> int:
    """
    Generate a unique build ID.
    """
    # TODO: Implement - maybe use UUIDs ? Will be unwieldly to pass them on the command line.
    # Or maybe use a hash of the "important" fields of the metadata (i.e. agent_components, artifact_type, artifact_format, worktree_diff, compatible_platforms)
    return 0
