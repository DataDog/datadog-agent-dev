# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import UTC, datetime
from functools import cached_property

from msgspec import Struct


class Commit(Struct, frozen=True, dict=True):  # noqa: PLW1641
    """
    A Git commit, identified by its SHA-1 hash.
    """

    sha1: str
    author: GitPersonDetails
    committer: GitPersonDetails
    message: str

    def __post_init__(self) -> None:
        if len(self.sha1) != 40:  # noqa: PLR2004
            msg = "SHA-1 hash must be 40 characters long"
            raise ValueError(msg)

    def __str__(self) -> str:
        return self.sha1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Commit) and self.sha1 == other.sha1

    @cached_property
    def committer_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.committer.timestamp, tz=UTC)

    @cached_property
    def author_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.author.timestamp, tz=UTC)


class GitPersonDetails(Struct, frozen=True):
    """
    Details of a person in Git (author or committer), including their name, email, and timestamp.
    """

    name: str
    email: str
    timestamp: int
