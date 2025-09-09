# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property

from dda.tools.base import Tool
from dda.utils.git.constants import GitAuthorEnvVars


class Git(Tool):
    """
    Example usage:

    ```python
    app.tools.git.run(["status"])
    ```
    """

    def env_vars(self) -> dict[str, str]:
        name = self.app.config.tools.git.author.name.strip()
        email = self.app.config.tools.git.author.email.strip()
        result = {}
        if name:
            result[GitAuthorEnvVars.NAME] = name
            result[GitAuthorEnvVars.COMMITTER_NAME] = name
        if email:
            result[GitAuthorEnvVars.EMAIL] = email
            result[GitAuthorEnvVars.COMMITTER_EMAIL] = email
        return result

    @cached_property
    def path(self) -> str:
        import shutil

        return shutil.which("git") or "git"

    def format_command(self, command: list[str]) -> list[str]:
        return [self.path, *command]

    @cached_property
    def author_name(self) -> str:
        """
        Get the git author name from dda config, env var, or by querying the global git config.
        Note that the global git config should itself read the env var if it exists - we manually read the env var as a performance optimization.
        """
        from os import environ

        if env_username := environ.get(GitAuthorEnvVars.NAME):
            return env_username

        # Don't use global in case some repo-specific config overrides it.
        # If no repo-specific config, the global config will be used automatically by git.
        return self.capture(["config", "--get", "user.name"]).strip()

    @cached_property
    def author_email(self) -> str:
        """
        Get the git author email from dda config, env var, or by querying the global git config.
        Note that the global git config should itself read the env var if it exists - we manually read the env var as a performance optimization.
        """
        from os import environ

        if env_email := environ.get(GitAuthorEnvVars.EMAIL):
            return env_email

        return self.capture(["config", "--get", "user.email"]).strip()
