# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any

from dda.utils.network.http.manager import HTTPClientManager


class GitHubHTTPClientManager(HTTPClientManager):
    """
    A subclass of [`HTTPClientManager`][dda.utils.network.http.manager.HTTPClientManager] for GitHub API requests.

    Authentication will use the [`GitHubAuth`][dda.config.model.github.GitHubAuth] configuration if both the
    user and token are set.
    """

    def set_default_client_config(self, config: dict[str, Any]) -> None:
        if "auth" not in config:
            github_auth = self.app.config.github.auth
            if github_auth.user and github_auth.token:
                config["auth"] = (github_auth.user, github_auth.token)

        super().set_default_client_config(config)
