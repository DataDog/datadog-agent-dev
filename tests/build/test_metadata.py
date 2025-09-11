# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import platform
from datetime import UTC, datetime
from typing import Any

import msgspec
import pytest

from dda.build.metadata.enums import OS, Arch, ArtifactFormat, ArtifactType
from dda.build.metadata.metadata import BuildMetadata
from dda.config.model import dec_hook, enc_hook
from dda.utils.fs import Path
from dda.utils.git.changeset import ChangedFile, ChangeSet, ChangeType
from dda.utils.git.commit import Commit, GitPersonDetails


@pytest.fixture
def example_author() -> GitPersonDetails:
    return GitPersonDetails(name="John Doe", email="john.doe@example.com", timestamp=1717171717)


@pytest.fixture
def example_commit(example_author: GitPersonDetails) -> Commit:
    return Commit(sha1="1234567890" * 4, author=example_author, committer=example_author, message="test")


def assert_metadata_equal(metadata: BuildMetadata, expected: BuildMetadata | dict[str, Any]) -> None:
    get = dict.get if isinstance(expected, dict) else getattr

    assert metadata.agent_components == get(expected, "agent_components")  # type: ignore[arg-type]
    assert metadata.artifact_format == get(expected, "artifact_format")  # type: ignore[arg-type]
    assert metadata.artifact_type == get(expected, "artifact_type")  # type: ignore[arg-type]
    assert metadata.commit == get(expected, "commit")  # type: ignore[arg-type]
    assert metadata.compatible_platforms == get(expected, "compatible_platforms")  # type: ignore[arg-type]
    assert metadata.build_platform == get(expected, "build_platform")  # type: ignore[arg-type]
    assert metadata.build_time == get(expected, "build_time")  # type: ignore[arg-type]
    assert metadata.worktree_diff == get(expected, "worktree_diff")  # type: ignore[arg-type]


class TestMetadata:
    def test_basic(self, example_commit: Commit) -> None:
        now = datetime.now(tz=UTC)
        commit = example_commit
        metadata = BuildMetadata(
            id=0,
            agent_components={"core-agent"},
            artifact_format=ArtifactFormat.BIN,
            artifact_type=ArtifactType.COMP,
            commit=commit,
            compatible_platforms={(OS.LINUX, Arch.AMD64)},
            build_platform=(OS.LINUX, Arch.AMD64),
            build_time=now,
            worktree_diff=ChangeSet({}),
        )
        expected = {
            "agent_components": {"core-agent"},
            "artifact_format": ArtifactFormat.BIN,
            "artifact_type": ArtifactType.COMP,
            "commit": example_commit,
            "compatible_platforms": {(OS.LINUX, Arch.AMD64)},
            "build_platform": (OS.LINUX, Arch.AMD64),
            "build_time": now,
            "worktree_diff": ChangeSet({}),
        }
        assert_metadata_equal(metadata, expected)

    @pytest.mark.parametrize(
        ("command_path", "expected"),
        [
            ("dda build comp core-agent", ({"core-agent"}, ArtifactType.COMP, ArtifactFormat.BIN)),
            (
                "dda build dist deb -c core-agent -c process-agent",
                ({"core-agent", "process-agent"}, ArtifactType.DIST, ArtifactFormat.DEB),
            ),
        ],
    )
    def test_this(self, app, mocker, command_path, expected, example_commit):
        # Expected values
        expected_agent_components, expected_artifact_type, expected_artifact_format = expected
        build_platform = (OS.from_alias(platform.system().lower()), Arch.from_alias(platform.machine()))
        expected = {
            "id": 0,
            "agent_components": expected_agent_components,
            "artifact_type": expected_artifact_type,
            "artifact_format": expected_artifact_format,
            "commit": example_commit,
            "compatible_platforms": {build_platform},
            "build_platform": build_platform,
            "build_time": datetime.now(),  # noqa: DTZ005
            "worktree_diff": ChangeSet([
                ChangedFile(path=Path("test.txt"), type=ChangeType.ADDED, patch="@@ -0,0 +1 @@\n+test", binary=False)
            ]),
        }

        # Setup mocks
        ctx = mocker.MagicMock()
        ctx.command_path = command_path
        mocker.patch("dda.build.metadata.metadata.generate_build_id", return_value=expected["id"])
        mocker.patch("dda.tools.git.Git.get_commit", return_value=expected["commit"])
        mocker.patch("dda.tools.git.Git.get_changes", return_value=expected["worktree_diff"])

        # Can't directly patch datetime.now because it's a builtin
        patched_datetime = mocker.patch("dda.build.metadata.metadata.datetime")
        patched_datetime.now.return_value = expected["build_time"]

        # Test without special arguments
        metadata = BuildMetadata.this(ctx, app)

        assert_metadata_equal(metadata, expected)

        # Test with passed compatible platforms
        expected["compatible_platforms"] = {(OS.MACOS, Arch.ARM64), (OS.LINUX, Arch.AMD64)}
        metadata = BuildMetadata.this(
            ctx,
            app,
            compatible_platforms=expected["compatible_platforms"],
        )
        assert_metadata_equal(metadata, expected)

    @pytest.mark.parametrize(
        "obj_data",
        [
            {
                "id": 1234,
                "agent_components": {"core-agent"},
                "artifact_format": ArtifactFormat.BIN,
                "artifact_type": ArtifactType.COMP,
                "compatible_platforms": {(OS.LINUX, Arch.AMD64)},
                "build_platform": (OS.LINUX, Arch.AMD64),
                "build_time": datetime.now(UTC),
            },
            {
                "id": 56789,
                "agent_components": {"core-agent", "trace-agent"},
                "artifact_format": ArtifactFormat.RPM,
                "artifact_type": ArtifactType.DIST,
                "compatible_platforms": {(OS.LINUX, Arch.AMD64), (OS.MACOS, Arch.ARM64)},
                "build_platform": (OS.MACOS, Arch.ARM64),
                "build_time": datetime.now(UTC),
            },
        ],
    )
    class TestEncodeDecode:
        def test_basic(self, obj_data, example_commit):
            obj = BuildMetadata(**obj_data, commit=example_commit, worktree_diff=ChangeSet({}))
            encoded_obj = msgspec.json.encode(obj, enc_hook=enc_hook)
            decoded_obj = msgspec.json.decode(encoded_obj, type=BuildMetadata, dec_hook=dec_hook)
            assert_metadata_equal(decoded_obj, obj)

        def test_with_changeset(self, obj_data, example_commit):
            changes = ChangeSet([
                ChangedFile(
                    path=Path("test.txt"),
                    type=ChangeType.ADDED,
                    patch="@@ -0,0 +1 @@\n+test",
                    binary=False,
                )
            ])
            obj = BuildMetadata(**obj_data, commit=example_commit, worktree_diff=changes)
            encoded_obj = msgspec.json.encode(obj, enc_hook=enc_hook)
            decoded_obj = msgspec.json.decode(encoded_obj, type=BuildMetadata, dec_hook=dec_hook)
            assert_metadata_equal(decoded_obj, obj)
