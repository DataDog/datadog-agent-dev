# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import Tool

if TYPE_CHECKING:
    from typing import Any

    from dda.utils.fs import Path
    from dda.utils.git.commit import Commit


class Git(Tool):
    """
    Example usage:

    ```python
    app.tools.git.run(["status"])
    ```
    """

    AUTHOR_NAME_ENV_VAR = "GIT_AUTHOR_NAME"
    AUTHOR_EMAIL_ENV_VAR = "GIT_AUTHOR_EMAIL"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        detected_name = self._query_author_name(self, check=False)
        config_name = self.app.config.user.name

        if detected_name and config_name and detected_name != config_name:
            self.app.display_warning(
                f"Git author name '{detected_name}' does not match the one configured in dda config: '{config_name}'. "
                "This can cause unexpected behavior - considering updating your global git config or the dda config.",
            )

        detected_email = self._query_author_email(self, check=False)
        config_email = self.app.config.user.email

        if detected_email and config_email and detected_email != config_email:
            self.app.display_warning(
                f"Git author email '{detected_email}' does not match the one configured in dda config: '{config_email}'. "
                "This can cause unexpected behavior - consider updating your global git config or the dda config.",
            )

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

        if cfg_username := self.app.config.user.name:
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

        if cfg_email := self.app.config.user.email:
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

    # === PRETEMPLATED COMMANDS === #
    def get_remote_details(self, repo_path: Path | None = None, remote_name: str = "origin") -> tuple[str, str, str]:
        """
        Get the details of the given remote for the Git repository at the given path.
        If no path is given, use the current working directory.
        The returned tuple is (org, repo, url).
        """
        from dda.utils.fs import Path

        repo_path = Path(repo_path or ".").resolve()
        remote_url = self.capture(
            ["config", "--get", f"remote.{remote_name}.url"],
            cwd=str(repo_path),
        ).strip()

        if remote_url.startswith("git@"):
            # Format is git@<website>:org/repo(.git)
            _, path = remote_url.split(":", 1)
            path.removesuffix(".git")
            org, repo = path.split("/", 1)
            return org, repo, remote_url

        # Format is https://<website>/org/repo(.git)
        org, repo = remote_url.removesuffix(".git").rsplit("/", 2)[-2:]
        return org, repo, remote_url

    def get_head_commit(self, repo_path: Path | None = None) -> Commit:
        """
        Get the current HEAD commit of the Git repository at the given path.
        If no path is given, use the current working directory.
        """
        from dda.utils.fs import Path
        from dda.utils.git.commit import Commit
        from dda.utils.git.sha1hash import SHA1Hash

        repo_path = Path(repo_path or ".").resolve()
        sha1_str = self.capture(["rev-parse", "HEAD"], cwd=str(repo_path)).strip()
        sha1 = SHA1Hash(sha1_str)

        # Get the org/repo from the remote URL
        org, repo, _ = self.get_remote_details(repo_path)
        return Commit(org=org, repo=repo, sha1=sha1)
