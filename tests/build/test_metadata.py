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

from dda.build.metadata.digests import ArtifactDigest, DigestType
from dda.build.metadata.formats import ArtifactFormat, ArtifactType
from dda.build.metadata.metadata import BuildMetadata, analyze_context
from dda.build.metadata.platforms import OS, Arch, Platform
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
        commit=example_commit,
        compatible_platforms={Platform(OS.LINUX, Arch.AMD64), Platform(OS.MACOS, Arch.ARM64)},
        build_platform=Platform(OS.MACOS, Arch.ARM64),
        build_time=datetime.fromisoformat("2025-09-16T12:54:34.820949Z"),
        worktree_diff=ChangeSet([
            ChangedFile(
                path=Path("test.txt"),
                type=ChangeType.ADDED,
                patch="@@ -0,0 +1 @@\n+test",
                binary=False,
            )
        ]),
        digest=ArtifactDigest(
            value="4a23f9863c45f043ececc0f82bf95ae9e4ff377ec2bb587a61ea7a75a3621115", type=DigestType.FILE_SHA256
        ),
    )


def assert_metadata_equal(metadata: BuildMetadata, expected: BuildMetadata | dict[str, Any]) -> None:
    get = dict.get if isinstance(expected, dict) else getattr

    assert metadata.agent_components == get(expected, "agent_components")  # type: ignore[arg-type]
    assert metadata.artifact_format == get(expected, "artifact_format")  # type: ignore[arg-type]
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
            commit=commit,
            compatible_platforms={Platform(OS.LINUX, Arch.AMD64)},
            build_platform=Platform(OS.LINUX, Arch.AMD64),
            build_time=now,
            worktree_diff=ChangeSet({}),
            digest=ArtifactDigest(value="0" * 64, type=DigestType.FILE_SHA256),
        )
        expected = {
            "agent_components": {"core-agent"},
            "artifact_format": ArtifactFormat.BIN,
            "commit": example_commit,
            "compatible_platforms": {Platform(OS.LINUX, Arch.AMD64)},
            "build_platform": Platform(OS.LINUX, Arch.AMD64),
            "build_time": now,
            "worktree_diff": ChangeSet({}),
            "file_hash": "0" * 64,
        }
        assert_metadata_equal(metadata, expected)

    @pytest.mark.parametrize(
        ("command_path", "expected"),
        [
            (
                "dda build comp core-agent",
                ({"core-agent"}, ArtifactFormat.BIN),
            ),
            (
                "dda build dist deb -c core-agent -c process-agent",
                (
                    {"core-agent", "process-agent"},
                    ArtifactFormat.DEB,
                ),
            ),
            (
                "dda build dist oci -c core-agent -c process-agent",
                (
                    {"core-agent", "process-agent"},
                    ArtifactFormat.OCI,
                ),
            ),
        ],
    )
    def test_analyze_context(self, app, mocker, command_path, expected, example_commit):
        # Expected values
        expected_agent_components, expected_artifact_format = expected
        build_platform = Platform.from_alias(platform.system(), platform.machine())
        expected = {
            "agent_components": expected_agent_components,
            "artifact_format": expected_artifact_format,
            "commit": example_commit,
            "compatible_platforms": {build_platform},
            "build_platform": build_platform,
            "worktree_diff": ChangeSet([
                ChangedFile(path=Path("test.txt"), type=ChangeType.ADDED, patch="@@ -0,0 +1 @@\n+test", binary=False)
            ]),
        }

        # Setup mocks
        ctx = mocker.MagicMock()
        ctx.command_path = command_path
        mocker.patch("dda.tools.git.Git.get_commit", return_value=expected["commit"])
        mocker.patch("dda.tools.git.Git.get_changes", return_value=expected["worktree_diff"])

        # Test without special arguments
        context_details = analyze_context(ctx, app)

        for field in expected:
            assert getattr(context_details, field) == expected[field]

    @pytest.mark.parametrize(
        "obj_data",
        [
            {
                "id": UUID("12345678-0000-0000-0000-000000000000"),
                "agent_components": {"core-agent"},
                "artifact_format": ArtifactFormat.BIN,
                "compatible_platforms": {Platform(OS.LINUX, Arch.AMD64)},
                "build_platform": Platform(OS.LINUX, Arch.AMD64),
                "build_time": datetime.now(UTC),
                "digest": ArtifactDigest(value="0" * 64, type=DigestType.FILE_SHA256),
            },
            {
                "id": UUID("00000000-0000-0000-0000-123456780000"),
                "agent_components": {"core-agent", "trace-agent"},
                "artifact_format": ArtifactFormat.RPM,
                "compatible_platforms": {Platform(OS.LINUX, Arch.AMD64), Platform(OS.MACOS, Arch.ARM64)},
                "build_platform": Platform(OS.MACOS, Arch.ARM64),
                "build_time": datetime.now(UTC),
                "digest": ArtifactDigest(value="0" * 64, type=DigestType.FILE_SHA256),
            },
            {
                "id": UUID("00000000-0000-0000-0000-123456780000"),
                "agent_components": {"core-agent"},
                "artifact_format": ArtifactFormat.OTHER,
                "compatible_platforms": {Platform(OS.MACOS, Arch.ARM64)},
                "build_platform": Platform(OS.MACOS, Arch.ARM64),
                "build_time": datetime.now(UTC),
                "digest": ArtifactDigest(value="i am a really weird digest", type=DigestType.OTHER),
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
                # We might have lists of dicts, so use dict.values() as a key for sorting
                def sorter(x):
                    return list(x.values()) if isinstance(x, dict) else x

                assert sorted(encoded_value, key=sorter) == sorted(expected_value, key=sorter)
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
                    "compatible_platforms": {Platform(OS.LINUX, Arch.AMD64)},
                    "build_platform": Platform(OS.MACOS, Arch.ARM64),
                    "build_time": datetime.now(UTC),
                    "digest": ArtifactDigest(value="0" * 64, type=DigestType.FILE_SHA256),
                },
                "core,trace-linux-amd64-12345678-db5fec1a.rpm",
            ),
            (
                {
                    "id": UUID("db5fec1a-7fce-42e9-a29b-13a8cc6a5493"),
                    "agent_components": {"dogstatd"},
                    "artifact_format": ArtifactFormat.BIN,
                    "compatible_platforms": {Platform(OS.LINUX, Arch.AMD64)},
                    "build_platform": Platform(OS.MACOS, Arch.ARM64),
                    "build_time": datetime.now(UTC),
                    "digest": ArtifactDigest(value="0" * 64, type=DigestType.FILE_SHA256),
                    "worktree_diff": ChangeSet([
                        ChangedFile(
                            path=Path("test.txt"),
                            type=ChangeType.ADDED,
                            patch="@@ -0,0 +1 @@\n+test",
                            binary=False,
                        ),
                    ]),
                },
                "dogstatd-linux-amd64-12345678+c7bcba44-db5fec1a",
            ),
            (
                {
                    "id": UUID("db5fec1a-7fce-42e9-a29b-13a8cc6a5493"),
                    "agent_components": {"core-agent", "system-probe", "dogstatsd"},
                    "artifact_format": ArtifactFormat.OCI,
                    "compatible_platforms": {
                        Platform(OS.LINUX, Arch.AMD64),
                        Platform(OS.MACOS, Arch.ARM64),
                        Platform(OS.LINUX, Arch.ARM64),
                        Platform(OS.MACOS, Arch.AMD64),
                    },
                    "build_platform": Platform(OS.MACOS, Arch.ARM64),
                    "build_time": datetime.now(UTC),
                    "digest": ArtifactDigest(value="sha256:" + "0" * 64, type=DigestType.OCI_DIGEST),
                },
                "core,dogstatsd,system_probe-many-12345678-db5fec1a-oci.tar.gz",
            ),
        ],
    )
    def test_get_canonical_filename(self, obj_data, example_commit, expected):
        if "worktree_diff" not in obj_data:
            obj_data["worktree_diff"] = ChangeSet({})
        obj = BuildMetadata(**obj_data, commit=example_commit)
        assert obj.get_canonical_filename() == expected


class TestDigest:
    def test_calculate_digest(self, app, mocker):
        # Setup mocks
        mocker.patch("dda.utils.fs.Path.hexdigest", return_value="0" * 64)
        mocker.patch("dda.tools.docker.Docker.get_image_digest", return_value="sha256:" + "0" * 64)

        # Test
        digest = DigestType.FILE_SHA256.calculate_digest(app, "test.txt")
        assert digest.value == "0" * 64
        assert digest.type == DigestType.FILE_SHA256

        digest = DigestType.OCI_DIGEST.calculate_digest(app, "test.txt")
        assert digest.value == "sha256:" + "0" * 64
        assert digest.type == DigestType.OCI_DIGEST

        with pytest.raises(NotImplementedError):
            DigestType.OTHER.calculate_digest(app, "test.txt")


class TestEncodeDecodeOtherValues:
    """Test that we can encode and decode other values that are not part of the enum."""

    def test_other_digest_type(self):
        digest_type = DigestType.OTHER
        encoded_digest_type = msgspec.json.encode(digest_type, enc_hook=enc_hook)
        decoded_digest_type = msgspec.json.decode(encoded_digest_type, type=DigestType, dec_hook=dec_hook)
        assert decoded_digest_type == DigestType.OTHER

        # Test that an unknown digest type is decoded as OTHER
        decoded_digest = msgspec.json.decode(b'"i am a really weird digest"', type=DigestType, dec_hook=dec_hook)
        assert decoded_digest == DigestType.OTHER

    def test_other_artifact_format(self):
        artifact_format = ArtifactFormat.OTHER
        encoded_artifact_format = msgspec.json.encode(artifact_format, enc_hook=enc_hook)
        decoded_artifact_format = msgspec.json.decode(encoded_artifact_format, type=ArtifactFormat, dec_hook=dec_hook)
        assert decoded_artifact_format == ArtifactFormat.OTHER

        # Test that an unknown artifact format is decoded as OTHER
        decoded_artifact_format = msgspec.json.decode(
            b'"i am a really weird artifact format"', type=ArtifactFormat, dec_hook=dec_hook
        )
        assert decoded_artifact_format == ArtifactFormat.OTHER

    def test_other_artifact_type(self):
        artifact_type = ArtifactType.OTHER
        encoded_artifact_type = msgspec.json.encode(artifact_type, enc_hook=enc_hook)
        decoded_artifact_type = msgspec.json.decode(encoded_artifact_type, type=ArtifactType, dec_hook=dec_hook)
        assert decoded_artifact_type == ArtifactType.OTHER

        # Test that an unknown artifact type is decoded as OTHER
        decoded_artifact_type = msgspec.json.decode(
            b'"i am a really weird artifact type"', type=ArtifactType, dec_hook=dec_hook
        )
        assert decoded_artifact_type == ArtifactType.OTHER
