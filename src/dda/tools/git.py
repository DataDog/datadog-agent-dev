# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import Tool

if TYPE_CHECKING:
    from typing import Any


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

    # === NOTE === #
    # The following functions are used by dda internals:
    # - as default_factories in the config for setting up git author name/email
    # - by telemetry to identify users if for some reason the config/env var is not set
    # - by the linux_container environment to pass the git author name/email to the container
    #
    # When generating the dda config, the Application object is not yet available.
    # It is therefore not possible to instantiate any Tool class at that point.
    # To work around this, these functions can be called statically with an _optional_ `tool` param
    # ============= #
    @staticmethod
    def _query_author_name(tool: Git | None = None, **kwargs: Any) -> str:
        """Query the global git config for the author name. This function can be used in a static context."""
        from dda.tools.base import static_tool_capture

        return static_tool_capture(["git", "config", "--global", "--get", "user.name"], tool, **kwargs).strip()

    @staticmethod
    def _query_author_email(tool: Git | None = None, **kwargs: Any) -> str:
        """Query the global git config for the author email. This function can be used in a static context."""
        from dda.tools.base import static_tool_capture

        return static_tool_capture(["git", "config", "--global", "--get", "user.email"], tool, **kwargs).strip()

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

        return self._query_author_name(self)

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

        return self._query_author_email(self)

    @cached_property
    def author_name(self) -> str:
        return self.get_author_name()

    @cached_property
    def author_email(self) -> str:
        return self.get_author_email()
