# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import UTC, datetime
from functools import cached_property

from msgspec import Struct


class Commit(Struct, frozen=True):
    """
    A Git commit, identified by its SHA-1 hash.
    """

    sha1: str

    def __post_init__(self) -> None:
        if len(self.sha1) != 40:  # noqa: PLR2004
            msg = "SHA-1 hash must be 40 characters long"
            raise ValueError(msg)

    def __str__(self) -> str:
        return self.sha1


class CommitDetails(Struct, dict=True):
    author_details: tuple[str, str]
    commiter_details: tuple[str, str]
    timestamp: int
    message: str

    @cached_property
    def commit_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=UTC)
