# SPDX-License-Identifier: MIT
#
# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>

from __future__ import annotations

import re

from msgspec import Struct

# TODO: Add tests
# TODO: Add all the versioning logic from the old invoke task


class SemanticVersion(Struct):
    major: int
    minor: int
    patch: int
    pre: str  # e.g. "devel"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}{f'-{self.pre}' if self.pre else ''}"


class AgentVersion(Struct):
    tag: SemanticVersion
    commits_since_tag: int
    commit_hash: str  # Does not have to be the full commit hash, just the first 7 characters

    def __str__(self) -> str:
        # Format: 7.74.0-devel+git.96.e927e2b
        return f"{self.tag}+git.{self.commits_since_tag}.{self.commit_hash[:7]}"


def parse_describe_result(describe_result: str) -> AgentVersion:
    """
    Parse the result of `git describe --tags` into an AgentVersion.
    """
    match = re.match(
        r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:-(?P<pre>[\w\.]+))?-(?P<commits_since_tag>\d+)-g(?P<commit_hash>[0-9a-f]+)$",
        describe_result.strip(),
    )
    if not match:
        msg = f"Failed to parse describe result: {describe_result}"
        raise RuntimeError(msg)
    return AgentVersion(
        tag=SemanticVersion(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            pre=match.group("pre"),
        ),
        commits_since_tag=int(match.group("commits_since_tag")),
        commit_hash=match.group("commit_hash"),
    )
