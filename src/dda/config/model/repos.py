# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec

if TYPE_CHECKING:
    from dda.cli.application import Application


class RepoConfig(msgspec.Struct, frozen=True, omit_defaults=True):
    # For org entries (e.g. "DataDog", "ddoghq"): SSH URL prefix such as
    # "git@github.com:DataDog". For per-repo entries: the full clone URL.
    url: str | None = None


def default_repos() -> dict[str, RepoConfig]:
    return {
        "DataDog": RepoConfig(url="git@github.com:DataDog"),
        "ddoghq": RepoConfig(url="git@github.com:ddoghq"),
    }


def resolve_clone_url(app: Application, repo: str, org: str = "DataDog") -> str:
    """Return the clone URL for *repo*.

    Looks for a per-repo override in ``[repos.{repo}]`` first; falls back to
    ``[repos.{org}].url/{repo}.git``.  Raises ``KeyError`` if neither is
    configured — this shouldn't happen with the default config.
    """
    direct = app.config.repos.get(repo)
    if direct is not None and direct.url is not None:
        return direct.url
    org_cfg = app.config.repos.get(org)
    if org_cfg is None or org_cfg.url is None:
        msg = f"No clone URL configured for repo '{repo}' and no '{org}' org entry in [repos]. Add [repos.{org}] url = \"git@...\" to your config."
        raise KeyError(msg)
    return f"{org_cfg.url.rstrip('/')}/{repo}.git"
