# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field


class GitHubAuth(Struct, frozen=True):
    user: str = ""
    token: str = ""


class GitHubConfig(Struct, frozen=True):
    auth: GitHubAuth = field(default_factory=GitHubAuth)
