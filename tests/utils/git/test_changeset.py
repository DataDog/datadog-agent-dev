# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import msgspec
import pytest

from dda.config.model import dec_hook, enc_hook
from dda.utils.fs import Path
from dda.utils.git.changeset import ChangedFile, ChangeSet, ChangeType
from tests.tools.git.conftest import REPO_TESTCASES


class TestFileChangesClass:
    def test_basic(self):
        file_changes = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        assert file_changes.path == Path("/path/to/file")
        assert file_changes.type == ChangeType.ADDED
        assert file_changes.patch == "patch"

    @pytest.mark.parametrize(
        "repo_testcase",
        REPO_TESTCASES,
    )
    def test_generate_from_diff_output(self, repo_testcase):
        fixtures_dir = (
            Path(__file__).parent.parent.parent / "tools" / "git" / "fixtures" / "repo_states" / repo_testcase
        )
        with open(fixtures_dir / "diff_output.txt", encoding="utf-8") as f:
            diff_output = f.read()

        with open(fixtures_dir / "expected_changeset.json", encoding="utf-8") as f:
            expected_changeset = msgspec.json.decode(f.read(), type=ChangeSet, dec_hook=dec_hook)

        expected_filechanges = sorted(
            expected_changeset.values(),
            key=lambda x: x.path.as_posix(),
        )

        seen_filechanges = sorted(ChangedFile.generate_from_diff_output(diff_output), key=lambda x: x.path.as_posix())

        assert len(seen_filechanges) == len(expected_filechanges)
        for seen, expected in zip(seen_filechanges, expected_filechanges, strict=True):
            assert seen.path == expected.path
            assert seen.type == expected.type
            assert seen.patch == expected.patch

    def test_encode_decode(self):
        file_changes = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        encoded_file_changes = msgspec.json.encode(file_changes, enc_hook=enc_hook)
        decoded_file_changes = msgspec.json.decode(encoded_file_changes, type=ChangedFile, dec_hook=dec_hook)
        assert decoded_file_changes == file_changes


class TestChangeSetClass:
    def test_basic(self):
        change = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        changeset = ChangeSet({change.path: change})
        assert changeset[Path("/path/to/file")] == change

    def test_add(self):
        change = ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch")
        changeset = ChangeSet.from_iter([change])
        assert changeset[Path("/path/to/file")] == change

    def test_digest(self):
        changes = [
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch"),
            ChangedFile(path=Path("file2"), type=ChangeType.MODIFIED, binary=False, patch="patch2"),
            ChangedFile(path=Path("/path/../file3"), type=ChangeType.DELETED, binary=False, patch="patch3"),
        ]
        changeset = ChangeSet.from_iter(changes)
        assert changeset.digest() == "aa2369871b3934e0dae9f141b5224704a7dffe5af614f8a31789322837fdcd85"

    def test_properties(self):
        changes = [
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch"),
            ChangedFile(path=Path("file2"), type=ChangeType.MODIFIED, binary=False, patch="patch2"),
            ChangedFile(path=Path("/path/../file3"), type=ChangeType.DELETED, binary=False, patch="patch3"),
        ]
        changeset = ChangeSet.from_iter(changes)
        assert changeset.added == {Path("/path/to/file")}
        assert changeset.modified == {Path("file2")}
        assert changeset.deleted == {Path("/path/../file3")}
        assert changeset.changed == {Path("/path/to/file"), Path("file2"), Path("/path/../file3")}

    @pytest.mark.parametrize(
        "repo_testcase",
        REPO_TESTCASES,
    )
    def test_generate_from_diff_output(self, repo_testcase):
        fixtures_dir = (
            Path(__file__).parent.parent.parent / "tools" / "git" / "fixtures" / "repo_states" / repo_testcase
        )
        with open(fixtures_dir / "diff_output.txt", encoding="utf-8") as f:
            diff_output = f.read()

        with open(fixtures_dir / "expected_changeset.json", encoding="utf-8") as f:
            expected_changeset = msgspec.json.decode(f.read(), type=ChangeSet, dec_hook=dec_hook)

        seen_changeset = ChangeSet.generate_from_diff_output(diff_output)

        assert seen_changeset.keys() == expected_changeset.keys()
        for file in seen_changeset:
            seen, expected = seen_changeset[file], expected_changeset[file]
            assert seen.path == expected.path
            assert seen.type == expected.type
            assert seen.patch == expected.patch

    def test_encode_decode(self):
        changes = [
            ChangedFile(path=Path("/path/to/file"), type=ChangeType.ADDED, binary=False, patch="patch"),
            ChangedFile(path=Path("file2"), type=ChangeType.MODIFIED, binary=False, patch="patch2"),
            ChangedFile(path=Path("/path/../file3"), type=ChangeType.DELETED, binary=False, patch="patch3"),
        ]
        changeset = ChangeSet.from_iter(changes)
        encoded_changeset = msgspec.json.encode(changeset, enc_hook=enc_hook)
        decoded_changeset = msgspec.json.decode(encoded_changeset, type=ChangeSet, dec_hook=dec_hook)
        assert decoded_changeset == changeset
