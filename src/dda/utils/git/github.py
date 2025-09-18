# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.utils.git.commit import Commit
    from dda.utils.git.remote import Remote


def get_github_url(remote: Remote) -> str:
    return f"https://github.com/{remote.full_repo}"


def get_github_api_url(remote: Remote) -> str:
    return f"https://api.github.com/repos/{remote.full_repo}"


def get_commit_github_url(remote: Remote, commit: Commit) -> str:
    return f"{get_github_url(remote)}/commit/{commit.sha1}"


def get_commit_github_api_url(remote: Remote, commit: Commit) -> str:
    return f"{get_github_api_url(remote)}/commits/{commit.sha1}"
