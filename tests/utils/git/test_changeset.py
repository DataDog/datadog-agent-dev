# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import msgspec
import pytest

from dda.types.hooks import dec_hook, enc_hook
from dda.utils.fs import Path
from dda.utils.git.changeset import ChangedFile, ChangeSet, ChangeType
from tests.tools.git.conftest import REPO_TESTCASES


class TestFileChangesClass:
    def test_basic(self):
        file_changes = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        assert file_changes.path == Path("/path/to/file")
        assert file_changes.type == ChangeType.ADDED
        assert file_changes.patch == "patch"

    def test_encode_decode(self):
        file_changes = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        encoded_file_changes = msgspec.json.encode(file_changes, enc_hook=enc_hook)
        decoded_file_changes = msgspec.json.decode(encoded_file_changes, type=ChangedFile, dec_hook=dec_hook)
        assert decoded_file_changes == file_changes


class TestChangeSetClass:
    def test_basic(self):
        change = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        changeset = ChangeSet([change])
        assert changeset.paths[str(change.path)] == change

    def test_add(self):
        change = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        changeset = ChangeSet([change])
        assert changeset.paths[str(change.path)] == change

    def test_digest(self):
        changes = [
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch"),
            ChangedFile(path=Path("file2"), type=ChangeType.MODIFIED, binary=False, patch="patch2"),
            ChangedFile(path=Path("/path/../file3"), type=ChangeType.DELETED, binary=False, patch="patch3"),
        ]
        changeset = ChangeSet(changes)
        assert changeset.digest() == "aa2369871b3934e0dae9f141b5224704a7dffe5af614f8a31789322837fdcd85"

    def test_properties(self):
        added = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        modified = ChangedFile(path=Path("file2"), type=ChangeType.MODIFIED, binary=False, patch="patch2")
        deleted = ChangedFile(path=Path("/path/../file3"), type=ChangeType.DELETED, binary=False, patch="patch3")
        changeset = ChangeSet([added, modified, deleted])
        assert changeset.added == {str(added.path): added}
        assert changeset.modified == {str(modified.path): modified}
        assert changeset.deleted == {str(deleted.path): deleted}
        assert changeset.paths == {str(added.path): added, str(modified.path): modified, str(deleted.path): deleted}

    def test_union(self):
        changeset1 = ChangeSet([
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        ])
        changeset2 = ChangeSet([
            ChangedFile(path=Path("/path/to/file2"), type=ChangeType.DELETED, binary=True, patch="patch2")
        ])
        assert changeset1 | changeset2 == ChangeSet([
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch"),
            ChangedFile(path=Path("/path/to/file2"), type=ChangeType.DELETED, binary=True, patch="patch2"),
        ])

    def test_eq(self):
        changeset1 = ChangeSet([
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        ])
        changeset2 = ChangeSet([
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        ])
        assert changeset1 == changeset2

    @pytest.mark.parametrize(
        "repo_testcase",
        REPO_TESTCASES,
    )
    def test_from_patches(self, repo_testcase):
        fixtures_dir = (
            Path(__file__).parent.parent.parent / "tools" / "git" / "fixtures" / "repo_states" / repo_testcase
        )
        with open(fixtures_dir / "diff_output.txt", encoding="utf-8") as f:
            diff_output = f.read()

        with open(fixtures_dir / "expected_changeset.json", encoding="utf-8") as f:
            expected_changeset = msgspec.json.decode(f.read(), type=ChangeSet, dec_hook=dec_hook)

        seen_changeset = ChangeSet.from_patches(diff_output)

        assert seen_changeset.paths == expected_changeset.paths

    def test_encode_decode(self):
        changes = [
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch"),
            ChangedFile(path=Path("file2"), type=ChangeType.MODIFIED, binary=False, patch="patch2"),
            ChangedFile(path=Path("/path/../file3"), type=ChangeType.DELETED, binary=False, patch="patch3"),
        ]
        changeset = ChangeSet(changes)
        encoded_changeset = msgspec.json.encode(changeset, enc_hook=enc_hook)
        decoded_changeset = msgspec.json.decode(encoded_changeset, type=ChangeSet, dec_hook=dec_hook)
        assert decoded_changeset == changeset
