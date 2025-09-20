# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import ExecutionContext, Tool
from dda.utils.git.constants import GitEnvVars

if TYPE_CHECKING:
    from collections.abc import Generator


class Git(Tool):
    """
    Example usage:

    ```python
    app.tools.git.run(["status"])
    ```
    """

    @contextmanager
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        author_name = self.app.config.tools.git.author.name.strip()
        author_email = self.app.config.tools.git.author.email.strip()
        env_vars = {}
        if author_name:
            env_vars[GitEnvVars.AUTHOR_NAME] = author_name
            env_vars[GitEnvVars.COMMITTER_NAME] = author_name
        if author_email:
            env_vars[GitEnvVars.AUTHOR_EMAIL] = author_email
            env_vars[GitEnvVars.COMMITTER_EMAIL] = author_email

        yield ExecutionContext(command=[self.path, *command], env_vars=env_vars)

    @cached_property
    def path(self) -> str:
        import shutil

        return shutil.which("git") or "git"

    @cached_property
    def author_name(self) -> str:
        """
        Get the git author name from dda config, env var, or by querying the global git config.
        Note that the global git config should itself read the env var if it exists - we manually read the env var as a performance optimization.
        """
        from os import environ

        if env_username := environ.get(GitEnvVars.AUTHOR_NAME):
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

        if env_email := environ.get(GitEnvVars.AUTHOR_EMAIL):
            return env_email

        return self.capture(["config", "--get", "user.email"]).strip()
