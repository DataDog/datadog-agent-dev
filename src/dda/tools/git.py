# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property

from dda.tools.base import Tool


class Git(Tool):
    """
    Example usage:

    ```python
    app.tools.git.run(["status"])
    ```
    """

    AUTHOR_NAME_ENV_VAR = "GIT_AUTHOR_NAME"
    AUTHOR_EMAIL_ENV_VAR = "GIT_AUTHOR_EMAIL"

    def env_vars(self) -> dict[str, str]:
        return {
            self.AUTHOR_NAME_ENV_VAR: self.app.config.tools.git.author_name.strip(),
            self.AUTHOR_EMAIL_ENV_VAR: self.app.config.tools.git.author_email.strip(),
        }

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

        # If the env var is set (either by the environment or because the user config is set to inherit),
        # Its value is what git will use for committing. We need to read it, as it might not correspond to the global git config.
        if env_username := (environ | self.env_vars()).get(self.AUTHOR_NAME_ENV_VAR):
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

        # See comment in author_name
        if env_email := (environ | self.env_vars()).get(self.AUTHOR_EMAIL_ENV_VAR):
            return env_email

        return self.capture(["config", "--get", "user.email"]).strip()
