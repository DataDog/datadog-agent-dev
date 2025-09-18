# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
from typing import TYPE_CHECKING, Any

from dda.tools.base import ExecutionContext, Tool
from dda.utils.git.changeset import ChangeSet
from dda.utils.git.constants import GitEnvVars
from dda.utils.git.remote import Remote

if TYPE_CHECKING:
    from collections.abc import Generator

    from dda.utils.fs import Path
    from dda.utils.git.commit import Commit, CommitDetails


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

    # === PRETEMPLATED COMMANDS === #
    def get_remote_details(self, remote_name: str = "origin") -> Remote:
        """
        Get the details of the given remote for the Git repository in the current working directory.
        The returned tuple is (org, repo, url).
        """

        remote_url = self.capture(
            ["config", "--get", f"remote.{remote_name}.url"],
        ).strip()

        return Remote.from_url(remote_url)

    def get_head_commit(self) -> Commit:
        """
        Get the current HEAD commit of the Git repository in the current working directory.
        """
        from dda.utils.git.commit import Commit

        sha1 = self.capture(["rev-parse", "HEAD"]).strip()

        return Commit(sha1=sha1)

    def get_commit_details(self, sha1: str) -> CommitDetails:
        """
        Get the details of the given commit in the Git repository in the current working directory.
        """
        from datetime import datetime

        from dda.utils.git.commit import CommitDetails

        raw_details = self.capture([
            "show",
            "--quiet",
            # Use a format that is easy to parse
            # fmt: author name, author email, author date, parent SHAs, commit message body
            "--format=%an%n%ae%n%ad%n%P%n%B",
            "--date=iso-strict",
            sha1,
        ])
        author_name, author_email, date_str, parents_str, *message_lines = raw_details.splitlines()

        return CommitDetails(
            author_name=author_name,
            author_email=author_email,
            datetime=datetime.fromisoformat(date_str),
            message="\n".join(message_lines).strip().strip('"'),
            parent_shas=list(parents_str.split()),
        )

    def commit_file(self, path: Path, *, content: str, commit_message: str) -> None:
        """
        Create and commit a single file with the given content.
        """
        path.write_text(content)
        self.run(["add", str(path)])  # Will fail if path is not under cwd
        self.run(["commit", "-m", commit_message])

    def _capture_diff_lines(self, *args: str, **kwargs: Any) -> list[str]:
        diff_args = [
            "-c",
            "core.quotepath=false",
            "diff",
            "-U0",
            "--no-color",
            "--no-prefix",
            "--no-renames",
            "--no-ext-diff",
        ]
        return self.capture([*diff_args, *args], check=False, **kwargs).strip().splitlines()

    def _compare_refs(self, ref1: str, ref2: str) -> ChangeSet:
        return ChangeSet.generate_from_diff_output(self._capture_diff_lines(ref1, ref2))

    def get_commit_changes(self, sha1: str) -> ChangeSet:
        """
        Get the changes of the given commit in the Git repository in the current working directory.
        """
        return self._compare_refs(f"{sha1}^", sha1)

    def get_changes_between_commits(self, a: str, b: str) -> ChangeSet:
        """
        Get the changes between two commits, identified by their SHA-1 hashes.
        """
        return self._compare_refs(a, b)

    def get_working_tree_changes(self) -> ChangeSet:
        """
        Get the changes in the working tree of the Git repository in the current working directory.
        """
        from os import environ

        from dda.utils.fs import temp_file

        with temp_file(suffix=".git_index") as temp_index_path:
            # Set up environment with temporary index
            temp_env = dict(environ)
            temp_env["GIT_INDEX_FILE"] = str(temp_index_path.resolve())
            self.run(["read-tree", "HEAD"], env=temp_env)

            # Get list of untracked files
            untracked_files_output = self.capture(
                ["ls-files", "--others", "--exclude-standard", "-z"], env=temp_env
            ).strip()
            untracked_files = [x.strip() for x in untracked_files_output.split("\0") if x.strip()]

            # Add untracked files to the index with --intent-to-add
            if untracked_files:
                self.run(["add", "--intent-to-add", *untracked_files], env=temp_env)

            # Get all changes (tracked + untracked) with a single diff command
            diff_lines = self._capture_diff_lines("HEAD", env=temp_env)

            return ChangeSet.generate_from_diff_output(diff_lines)

    def get_merge_base(self, remote_name: str = "origin") -> str:
        """
        Get the merge base of the current branch.
        """
        res = self.capture(["merge-base", "HEAD", remote_name], check=False).strip()
        if not res:
            self.app.display_warning("Could not determine merge base for current branch. Using `main` instead.")
            return "main"
        return res

    def get_changes_with_base(
        self,
        base: str | None = None,
        *,
        include_working_tree: bool = True,
        remote_name: str = "origin",
    ) -> ChangeSet:
        """
        Get the changes with the given base.
        By default, this base is the merge base of the current branch.
        If it cannot be determined, `main` will be used instead.

        If `include_working_tree` is True, the changes in the working tree will be included.
        If `remote_name` is provided, the changes will be compared to the branch in the remote with this name.
        """
        if base is None:
            base = self.get_merge_base(remote_name)

        head = self.get_head_commit()
        changes = ChangeSet.generate_from_diff_output(self._capture_diff_lines(base, "...", head.sha1))
        if include_working_tree:
            changes |= self.get_working_tree_changes()
        return changes
