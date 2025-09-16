# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import platform
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

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


@pytest.fixture
def example_build_metadata(example_commit: Commit) -> BuildMetadata:
    return BuildMetadata(
        id=UUID("00000000-0000-0000-0000-123456780000"),
        agent_components={"core-agent", "trace-agent"},
        artifact_format=ArtifactFormat.RPM,
        artifact_type=ArtifactType.DIST,
        commit=example_commit,
        compatible_platforms={(OS.LINUX, Arch.AMD64), (OS.MACOS, Arch.ARM64)},
        build_platform=(OS.MACOS, Arch.ARM64),
        build_time=datetime.fromisoformat("2025-09-16T12:54:34.820949Z"),
        worktree_diff=ChangeSet([
            ChangedFile(
                path=Path("test.txt"),
                type=ChangeType.ADDED,
                patch="@@ -0,0 +1 @@\n+test",
                binary=False,
            )
        ]),
        file_hash="4a23f9863c45f043ececc0f82bf95ae9e4ff377ec2bb587a61ea7a75a3621115",
    )


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
            id=UUID("00000000-0000-0000-0000-000000000000"),
            agent_components={"core-agent"},
            artifact_format=ArtifactFormat.BIN,
            artifact_type=ArtifactType.COMP,
            commit=commit,
            compatible_platforms={(OS.LINUX, Arch.AMD64)},
            build_platform=(OS.LINUX, Arch.AMD64),
            build_time=now,
            worktree_diff=ChangeSet({}),
            file_hash="0" * 64,
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
            "file_hash": "0" * 64,
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
            "id": UUID("00000000-0000-0000-0000-000000000000"),
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
            "file_hash": "0" * 64,
        }

        # Setup mocks
        ctx = mocker.MagicMock()
        ctx.command_path = command_path
        mocker.patch("dda.build.metadata.metadata.generate_build_id", return_value=expected["id"])
        mocker.patch("dda.tools.git.Git.get_commit", return_value=expected["commit"])
        mocker.patch("dda.tools.git.Git.get_changes", return_value=expected["worktree_diff"])
        mocker.patch("dda.build.metadata.metadata.calculate_file_hash", return_value=expected["file_hash"])

        # Can't directly patch datetime.now because it's a builtin
        patched_datetime = mocker.patch("dda.build.metadata.metadata.datetime")
        patched_datetime.now.return_value = expected["build_time"]
        # Test without special arguments
        metadata = BuildMetadata.this(
            ctx,
            app,
            Path("test.txt"),
        )

        assert_metadata_equal(metadata, expected)

        # Test with passed compatible platforms
        expected["compatible_platforms"] = {(OS.MACOS, Arch.ARM64), (OS.LINUX, Arch.AMD64)}
        metadata = BuildMetadata.this(
            ctx,
            app,
            Path("test.txt"),
            compatible_platforms=expected["compatible_platforms"],
        )
        assert_metadata_equal(metadata, expected)

    @pytest.mark.parametrize(
        "obj_data",
        [
            {
                "id": UUID("12345678-0000-0000-0000-000000000000"),
                "agent_components": {"core-agent"},
                "artifact_format": ArtifactFormat.BIN,
                "artifact_type": ArtifactType.COMP,
                "compatible_platforms": {(OS.LINUX, Arch.AMD64)},
                "build_platform": (OS.LINUX, Arch.AMD64),
                "build_time": datetime.now(UTC),
                "file_hash": "0" * 64,
            },
            {
                "id": UUID("00000000-0000-0000-0000-123456780000"),
                "agent_components": {"core-agent", "trace-agent"},
                "artifact_format": ArtifactFormat.RPM,
                "artifact_type": ArtifactType.DIST,
                "compatible_platforms": {(OS.LINUX, Arch.AMD64), (OS.MACOS, Arch.ARM64)},
                "build_platform": (OS.MACOS, Arch.ARM64),
                "build_time": datetime.now(UTC),
                "file_hash": "0" * 64,
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

    def test_to_file(self, temp_dir, example_build_metadata):
        path = temp_dir / "build_metadata.json"
        example_build_metadata.to_file(path)
        text = path.read_text(encoding="utf-8")

        expected = (Path(__file__).parent / "fixtures" / "build_metadata.json").read_text(encoding="utf-8")

        # Compare both decoded jsons are equal - we decode to avoid being affected by key ordering or whitespace
        encoded = json.loads(text)
        expected = json.loads(expected)

        encoded_keys = set(encoded.keys())
        expected_keys = set(expected.keys())
        assert encoded_keys == expected_keys
        for key in encoded_keys:
            encoded_value, expected_value = encoded[key], expected[key]
            if isinstance(encoded_value, list):
                assert sorted(encoded_value) == sorted(expected_value)
            else:
                assert encoded_value == expected_value

    def test_from_file(self, example_build_metadata):
        path = Path(__file__).parent / "fixtures" / "build_metadata.json"
        obj = BuildMetadata.from_file(path)
        assert_metadata_equal(obj, example_build_metadata)

    @pytest.mark.parametrize(
        ("obj_data", "expected"),
        [
            (
                {
                    "id": UUID("db5fec1a-7fce-42e9-a29b-13a8cc6a5493"),
                    "agent_components": {"core-agent", "trace-agent"},
                    "artifact_format": ArtifactFormat.RPM,
                    "artifact_type": ArtifactType.DIST,
                    "compatible_platforms": {(OS.LINUX, Arch.AMD64)},
                    "build_platform": (OS.MACOS, Arch.ARM64),
                    "build_time": datetime.now(UTC),
                    "file_hash": "0" * 64,
                },
                "core,trace-12345678-db5fec1a-linux-amd64.rpm",
            ),
            (
                {
                    "id": UUID("db5fec1a-7fce-42e9-a29b-13a8cc6a5493"),
                    "agent_components": {"dogstatd"},
                    "artifact_format": ArtifactFormat.BIN,
                    "artifact_type": ArtifactType.COMP,
                    "compatible_platforms": {(OS.LINUX, Arch.AMD64)},
                    "build_platform": (OS.MACOS, Arch.ARM64),
                    "build_time": datetime.now(UTC),
                    "file_hash": "0" * 64,
                    "worktree_diff": ChangeSet([
                        ChangedFile(
                            path=Path("test.txt"),
                            type=ChangeType.ADDED,
                            patch="@@ -0,0 +1 @@\n+test",
                            binary=False,
                        ),
                    ]),
                },
                "dogstatd-12345678+-db5fec1a-linux-amd64",
            ),
            (
                {
                    "id": UUID("db5fec1a-7fce-42e9-a29b-13a8cc6a5493"),
                    "agent_components": {"core-agent", "system-probe", "dogstatsd"},
                    "artifact_format": ArtifactFormat.DOCKER,
                    "artifact_type": ArtifactType.DIST,
                    "compatible_platforms": {
                        (OS.LINUX, Arch.AMD64),
                        (OS.MACOS, Arch.ARM64),
                        (OS.LINUX, Arch.ARM64),
                        (OS.MACOS, Arch.AMD64),
                    },
                    "build_platform": (OS.MACOS, Arch.ARM64),
                    "build_time": datetime.now(UTC),
                    "file_hash": "0" * 64,
                },
                "core,dogstatsd,system_probe-12345678-db5fec1a-many-dockerimage.tar.gz",
            ),
            (
                {
                    "id": UUID("db5fec1a-7fce-42e9-a29b-13a8cc6a5493"),
                    "agent_components": {"core-agent"},
                    "artifact_format": ArtifactFormat.CFG,
                    "artifact_type": ArtifactType.OTHER,
                    "compatible_platforms": {(OS.ANY, Arch.ANY)},
                    "build_platform": (OS.MACOS, Arch.ARM64),
                    "build_time": datetime.now(UTC),
                    "file_hash": "0" * 64,
                    "worktree_diff": ChangeSet([]),
                },
                "core-12345678-db5fec1a-any-config.tar.gz",
            ),
        ],
    )
    def test_get_canonical_filename(self, obj_data, example_commit, expected):
        if "worktree_diff" not in obj_data:
            obj_data["worktree_diff"] = ChangeSet({})
        obj = BuildMetadata(**obj_data, commit=example_commit)
        assert obj.get_canonical_filename() == expected
