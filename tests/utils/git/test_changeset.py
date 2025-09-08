# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import msgspec
import pytest

from dda.utils.fs import Path
from dda.utils.git.changeset import ChangeSet, ChangeType, FileChanges
from dda.utils.git.commit import SHA1Hash
from tests.tools.conftest import REPO_TESTCASES


class TestFileChangesClass:
    def test_basic(self):
        file_changes = FileChanges(file=Path("/path/to/file"), type=ChangeType.ADDED, patch="patch")
        assert file_changes.file == Path("/path/to/file")
        assert file_changes.type == ChangeType.ADDED
        assert file_changes.patch == "patch"

    @pytest.mark.parametrize(
        "repo_testcase",
        REPO_TESTCASES,
    )
    def test_generate_from_diff_output(self, repo_testcase):
        fixtures_dir = Path(__file__).parent.parent.parent / "tools" / "fixtures" / "repo_states" / repo_testcase
        with open(fixtures_dir / "diff_output.txt", encoding="utf-8") as f:
            diff_output = f.read()

        with open(fixtures_dir / "expected_changeset.json", encoding="utf-8") as f:
            expected_changeset = msgspec.json.decode(f.read(), type=ChangeSet, dec_hook=ChangeSet.dec_hook)

        expected_filechanges = sorted(
            expected_changeset.values(),
            key=lambda x: x.file.as_posix(),
        )

        seen_filechanges = sorted(FileChanges.generate_from_diff_output(diff_output), key=lambda x: x.file.as_posix())

        assert len(seen_filechanges) == len(expected_filechanges)
        for seen, expected in zip(seen_filechanges, expected_filechanges, strict=True):
            assert seen.file == expected.file
            assert seen.type == expected.type
            assert seen.patch == expected.patch

    @pytest.mark.parametrize(
        "input_dict",
        [
            {
                "file": "complex/repo/path/added_lines_middle.txt",
                "change_type": "modified",
                "patch": "@@ -2,0 +3,2 @@ I have a bit more text than added_lines.\n+Nobody expects the Spanish Inquisition !\n+My developer really wonders if cracking jokes in test data is against company policy.",
            },
            {
                "file": "simple/file2.txt",
                "change_type": "removed",
                "patch": "@@ -1,3 +0,0 @@\n-file2\n-I will be deleted, unfortunately.\n-That's quite sad.",
            },
            {
                "file": "hopefully/you/support/../../file6.txt",
                "change_type": "added",
                "patch": "@@ -0,0 +1,3 @@\n+file6\n+I am a new file in the repo !\n+That's incredible.",
            },
        ],
    )
    def test_from_dict(self, input_dict):
        seen_filechanges = FileChanges.from_dict(input_dict)
        assert seen_filechanges.file == Path(input_dict["file"])
        assert seen_filechanges.type == ChangeType.from_github_status(input_dict["change_type"])
        assert seen_filechanges.patch == input_dict["patch"]

    def test_encode_decode(self):
        file_changes = FileChanges(file=Path("/path/to/file"), type=ChangeType.ADDED, patch="patch")
        encoded_file_changes = msgspec.json.encode(file_changes, enc_hook=FileChanges.enc_hook)
        decoded_file_changes = msgspec.json.decode(
            encoded_file_changes, type=FileChanges, dec_hook=FileChanges.dec_hook
        )
        assert decoded_file_changes == file_changes


class TestChangeSetClass:
    def test_basic(self):
        change = FileChanges(file=Path("/path/to/file"), type=ChangeType.ADDED, patch="patch")
        changeset = ChangeSet({change.file: change})
        assert changeset[Path("/path/to/file")] == change

    def test_add(self):
        change = FileChanges(file=Path("/path/to/file"), type=ChangeType.ADDED, patch="patch")
        changeset = ChangeSet.from_iter([change])
        assert changeset[Path("/path/to/file")] == change

    def test_digest(self):
        changes = [
            FileChanges(file=Path("/path/to/file"), type=ChangeType.ADDED, patch="patch"),
            FileChanges(file=Path("file2"), type=ChangeType.MODIFIED, patch="patch2"),
            FileChanges(file=Path("/path/../file3"), type=ChangeType.DELETED, patch="patch3"),
        ]
        changeset = ChangeSet.from_iter(changes)
        assert changeset.digest() == SHA1Hash("95a9fe4d808bdda19da9285b6d1a31a6e29ddbfa")

    def test_properties(self):
        changes = [
            FileChanges(file=Path("/path/to/file"), type=ChangeType.ADDED, patch="patch"),
            FileChanges(file=Path("file2"), type=ChangeType.MODIFIED, patch="patch2"),
            FileChanges(file=Path("/path/../file3"), type=ChangeType.DELETED, patch="patch3"),
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
        fixtures_dir = Path(__file__).parent.parent.parent / "tools" / "fixtures" / "repo_states" / repo_testcase
        with open(fixtures_dir / "diff_output.txt", encoding="utf-8") as f:
            diff_output = f.read()

        with open(fixtures_dir / "expected_changeset.json", encoding="utf-8") as f:
            expected_changeset = msgspec.json.decode(f.read(), type=ChangeSet, dec_hook=ChangeSet.dec_hook)

        seen_changeset = ChangeSet.generate_from_diff_output(diff_output)

        assert seen_changeset.keys() == expected_changeset.keys()
        for file in seen_changeset:
            seen, expected = seen_changeset[file], expected_changeset[file]
            assert seen.file == expected.file
            assert seen.type == expected.type
            assert seen.patch == expected.patch

    def test_encode_decode(self):
        changes = [
            FileChanges(file=Path("/path/to/file"), type=ChangeType.ADDED, patch="patch"),
            FileChanges(file=Path("file2"), type=ChangeType.MODIFIED, patch="patch2"),
            FileChanges(file=Path("/path/../file3"), type=ChangeType.DELETED, patch="patch3"),
        ]
        changeset = ChangeSet.from_iter(changes)
        encoded_changeset = msgspec.json.encode(changeset, enc_hook=ChangeSet.enc_hook)
        decoded_changeset = msgspec.json.decode(encoded_changeset, type=ChangeSet, dec_hook=ChangeSet.dec_hook)
        assert decoded_changeset == changeset
