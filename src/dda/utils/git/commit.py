# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from msgspec import Struct

if TYPE_CHECKING:
    from datetime import datetime


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


class CommitDetails(Struct):
    author_name: str
    author_email: str
    datetime: datetime
    message: str
    parent_shas: list[str]
