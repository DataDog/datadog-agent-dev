# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from dda.tools.base import Tool

if TYPE_CHECKING:
    from dda.utils.fs import Path
    from dda.utils.git.changeset import ChangeSet
    from dda.utils.git.commit import Commit, CommitDetails, SHA1Hash


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
        if self.app.config.tools.git.author_details == "inherit":
            return {
                self.AUTHOR_NAME_ENV_VAR: self.app.config.user.name.strip(),
                self.AUTHOR_EMAIL_ENV_VAR: self.app.config.user.emails[0].strip(),
            }
        return {}

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
            path = remote_url.split(":", 1)[1].removesuffix(".git")
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
        from dda.utils.git.commit import Commit, SHA1Hash

        repo_path = Path(repo_path or ".").resolve()
        sha1_str = self.capture(["rev-parse", "HEAD"], cwd=str(repo_path)).strip()
        sha1 = SHA1Hash(sha1_str)

        # Get the org/repo from the remote URL
        org, repo, _ = self.get_remote_details(repo_path)
        return Commit(org=org, repo=repo, sha1=sha1)

    def get_commit_details(self, sha1: SHA1Hash, repo_path: Path | None = None) -> CommitDetails:
        """
        Get the details of the given commit in the Git repository at the given path.
        If no path is given, use the current working directory.
        """
        from datetime import datetime

        from dda.utils.fs import Path
        from dda.utils.git.commit import CommitDetails, SHA1Hash

        repo_path = Path(repo_path or ".").resolve()
        raw_details = self.capture(
            [
                "show",
                "--quiet",
                # Use a format that is easy to parse
                # fmt: author name, author email, author date, parent SHAs, commit message body
                "--format=%an%n%ae%n%ad%n%P%n%B",
                "--date=iso-strict",
                str(sha1),
            ],
            cwd=str(repo_path),
        )
        author_name, author_email, date_str, parents_str, *message_lines = raw_details.splitlines()

        return CommitDetails(
            author_name=author_name,
            author_email=author_email,
            datetime=datetime.fromisoformat(date_str),
            message="\n".join(message_lines).strip().strip('"'),
            parent_shas=[SHA1Hash(parent_sha) for parent_sha in parents_str.split()],
        )

    def get_commit_changes(self, sha1: SHA1Hash, repo_path: Path | None = None) -> ChangeSet:
        """
        Get the changes of the given commit in the Git repository at the given path.
        If no path is given, use the current working directory.
        """
        from dda.utils.fs import Path
        from dda.utils.git.changeset import FILECHANGES_GIT_DIFF_ARGS, ChangeSet

        repo_path = Path(repo_path or ".").resolve()
        return ChangeSet.generate_from_diff_output(
            self.capture([*FILECHANGES_GIT_DIFF_ARGS, f"{sha1}^", str(sha1)], cwd=str(repo_path)),
        )

    def get_working_tree_changes(self, repo_path: Path | None = None) -> ChangeSet:
        """
        Get the changes in the working tree of the Git repository at the given path.
        If no path is given, use the current working directory.
        """
        from itertools import chain

        from dda.utils.fs import Path
        from dda.utils.git.changeset import FILECHANGES_GIT_DIFF_ARGS, ChangeSet

        repo_path = Path(repo_path or ".").resolve()
        with repo_path.as_cwd():
            # Capture changes to already-tracked files - `diff HEAD` does not include any untracked files !
            tracked_changes = ChangeSet.generate_from_diff_output(self.capture([*FILECHANGES_GIT_DIFF_ARGS, "HEAD"]))

            # Capture changes to untracked files
            untracked_files = self.capture(["ls-files", "--others", "--exclude-standard"]).strip().splitlines()
            diffs = list(
                chain.from_iterable(
                    self.capture([*FILECHANGES_GIT_DIFF_ARGS, "/dev/null", file], check=False).strip().splitlines()
                    for file in untracked_files
                )
            )
            untracked_changes = ChangeSet.generate_from_diff_output(diffs)

        # Combine the changes
        return ChangeSet(tracked_changes | untracked_changes)
