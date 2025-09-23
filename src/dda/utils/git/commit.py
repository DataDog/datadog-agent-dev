# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any

from msgspec import Struct

from dda.utils.git.changeset import ChangeSet

if TYPE_CHECKING:
    from datetime import datetime

    from dda.cli.application import Application
    from dda.utils.git.remote import Remote


class Commit(Struct, frozen=True, dict=True):
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

    @classmethod
    def head(cls, app: Application) -> Commit:
        """
        Get the current HEAD commit of the Git repository in the current working directory.
        """
        return app.tools.git.get_head_commit()

    def compare_to(self, app: Application, other: Commit) -> ChangeSet:
        """
        Compare this commit to another commit.
        """
        return app.tools.git.get_changes_between_commits(self.sha1, other.sha1)

    def get_details_and_changes_from_remote(self, remote: Remote) -> tuple[CommitDetails, ChangeSet]:
        details, changes = remote.get_details_and_changes_for_commit(self)
        self.__dict__["details"] = details
        self.__dict__["changes"] = changes
        return details, changes

    def get_details_from_remote(self, remote: Remote) -> CommitDetails:
        return self.get_details_and_changes_from_remote(remote)[0]

    def get_details_from_git(self, app: Application) -> CommitDetails:
        """
        Get the details of this commit by querying the local Git repository.
        This requires an Application instance to access the Git tool.

        Prefer to use this method when possible, as it is much faster than querying the remote API.
        """
        self.__dict__["details"] = app.tools.git.get_commit_details(self.sha1)
        return self.details

    def get_changes_from_remote(self, remote: Remote) -> ChangeSet:
        return self.get_details_and_changes_from_remote(remote)[1]

    def get_changes_from_git(self, app: Application) -> ChangeSet:
        self.__dict__["changes"] = app.tools.git.get_commit_changes(self.sha1)
        return self.changes

    @cached_property
    def details(self) -> CommitDetails:
        msg = "Commit details have not been fetched yet. Call one of the get_details_from_*() methods first."
        raise AttributeError(msg)

    @cached_property
    def changes(self) -> ChangeSet:
        msg = "Commit changes have not been fetched yet. Call one of the get_changes_from_*() methods first."
        raise AttributeError(msg)

    # Proxy properties to access details directly from the Commit object
    @property
    def author_name(self) -> str:
        return self.details.author_name

    @property
    def author_email(self) -> str:
        return self.details.author_email

    @property
    def datetime(self) -> datetime:
        return self.details.datetime

    @property
    def message(self) -> str:
        return self.details.message

    @property
    def parent_shas(self) -> list[str]:
        return self.details.parent_shas

    @classmethod
    def enc_hook(cls, obj: Any) -> Any:
        # Only unsupported objects are ChangeSet objects
        return ChangeSet.enc_hook(obj)

    @classmethod
    def dec_hook(cls, obj_type: type, obj: Any) -> Any:
        # Only unsupported objects are ChangeSet objects
        return ChangeSet.dec_hook(obj_type, obj)


class CommitDetails(Struct):
    author_name: str
    author_email: str
    datetime: datetime
    message: str
    parent_shas: list[str]
