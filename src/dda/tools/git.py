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

    @cached_property
    def path(self) -> str:
        import shutil

        return shutil.which("git") or "git"

    def format_command(self, command: list[str]) -> list[str]:
        return [self.path, *command]

    # These properties are used on every command invocation by the telemetry system
    # so we cache them to avoid running git commands too often
    def get_author_name(self) -> str:
        """
        Get the git author name from dda config, env var, or by querying the global git config.
        Note that the global git config should itself read the env var if it exists - we manually read the env var as a performance optimization.
        """

        if cfg_username := self.app.config.tools.git.username:
            return cfg_username

        from os import environ

        if env_username := environ.get(self.AUTHOR_NAME_ENV_VAR):
            return env_username

        return self.capture(
            ["config", "--global", "--get", "user.name"],
        ).strip()

    def get_author_email(self) -> str:
        """
        Get the git author email from dda config, env var, or by querying the global git config.
        Note that the global git config should itself read the env var if it exists - we manually read the env var as a performance optimization.
        """

        if cfg_email := self.app.config.tools.git.user_email:
            return cfg_email

        from os import environ

        if env_email := environ.get(self.AUTHOR_EMAIL_ENV_VAR):
            return env_email

        return self.capture(
            ["config", "--global", "--get", "user.email"],
        ).strip()

    @cached_property
    def author_name(self) -> str:
        return self.get_author_name()

    @cached_property
    def author_email(self) -> str:
        return self.get_author_email()
