# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
from typing import TYPE_CHECKING, Any

from dda.tools.base import ExecutionContext, Tool
from dda.utils.git.changeset import ChangeSet
from dda.utils.git.commit import GitPersonDetails

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from dda.utils.fs import Path
    from dda.utils.git.commit import Commit
    from dda.utils.git.remote import Remote


class Git(Tool):
    """
    Example usage:

    ```python
    app.tools.git.run(["status"])
    ```
    """

    @contextmanager
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        from dda.utils.git.constants import GitEnvVars

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

        from dda.utils.git.constants import GitEnvVars

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

        from dda.utils.git.constants import GitEnvVars

        if env_email := environ.get(GitEnvVars.AUTHOR_EMAIL):
            return env_email

        return self.capture(["config", "--get", "user.email"]).strip()

    def get_remote(self, remote_name: str = "origin") -> Remote:
        """
        Get the details of the given remote for the Git repository in the current working directory.
        """
        from dda.utils.git.remote import Remote

        remote_url = self.capture(
            ["config", "--get", f"remote.{remote_name}.url"],
        ).strip()

        return Remote.from_url(remote_url)

    def get_commit(self, ref: str = "HEAD") -> Commit:
        """
        Get a Commit object from the Git repository in the current working directory for the given reference (default: HEAD).
        """
        from dda.utils.git.commit import Commit

        raw_details = self.capture([
            "--no-pager",
            "show",
            "--no-color",
            "--no-patch",
            "--quiet",
            # Use a format that is easy to parse
            # fmt: commit hash, commit subject, commit body, committer name, committer email, committer date, author name, author email, author date
            "--format=%H%x00%s%x00%b%x00%cn%x00%ce%x00%ct%x00%an%x00%ae%x00%at",
            f"{ref}^{{commit}}",
        ])

        # Extract parts
        parts = raw_details.split("\0")
        sha1, *parts = parts
        commit_subject, commit_body, *parts = parts
        committer_name, committer_email, commit_date, *parts = parts
        author_name, author_email, author_date = parts

        # Process parts

        # Will give a timestamp in UTC
        # we don't care what tz the author was in as long as we stay consistent and are able to display all times in the user's timezone
        commit_timestamp_str = commit_date.split(" ")[0]
        commit_timestamp = int(commit_timestamp_str)
        author_timestamp_str = author_date.split(" ")[0]
        author_timestamp = int(author_timestamp_str)
        message = (commit_subject + "\n\n" + commit_body).strip()

        author_details = GitPersonDetails(author_name, author_email, author_timestamp)
        committer_details = GitPersonDetails(committer_name, committer_email, commit_timestamp)

        return Commit(
            sha1=sha1,
            author=author_details,
            committer=committer_details,
            message=message,
        )

    def add(self, paths: Iterable[Path]) -> None:
        """
        Add the given paths to the index.
        Will fail if any path is not under cwd.
        """
        self.capture(["add", *map(str, paths)])

    def commit(self, message: str, *, allow_empty: bool = False) -> None:
        """
        Commit the changes in the index.
        """
        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
        self.capture(args)

    def commit_file(self, path: Path, *, content: str, commit_message: str) -> None:
        """
        Create and commit a single file with the given content.
        """
        path.write_text(content)
        self.add((path,))
        self.commit(commit_message)

    def _get_patch(self, *args: str, **kwargs: Any) -> str:
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
        return self.capture([*diff_args, *args], **kwargs).strip()

    def get_changes(
        self,
        ref: str = "HEAD",
        /,
        *,
        start: str | None = None,
        merge_base: bool = False,
        working_tree: bool = False,
        remote_name: str = "origin",
    ) -> ChangeSet:
        """
        Use `git` to compute a ChangeSet between two refs.

        Parameters:
            ref: The reference to compare to. Default is HEAD.
            start: The reference to compare from.
                Default is None, in which case the parent commit of the ref is used.
                If merge_base is also True, the merge base is used instead of the parent commit.
            merge_base: Whether to compute the differences between the refs starting from the merge base.
            working_tree: Whether to include the working tree changes. Default is False.
            remote_name: The name of the remote to compare to. Default is origin.

        Returns:
            A ChangeSet representing the differences between the refs.

        Examples:
            ```python
            # Get the changes of the HEAD commit
            changes = git.get_changes(ref="HEAD")

            # Get the changes between two commits
            changes = git.get_changes(ref=commit1.sha1, start=commit2.sha1)

            # Get the changes between the HEAD commit and the main branch
            changes = git.get_changes(ref="HEAD", start="origin/main")

            # Get the changes between the HEAD commit and the main branch starting from the merge base
            changes = git.get_changes(ref="HEAD", start="origin/main", merge_base=True)

            # Get _only_ the working tree changes
            changes = git.get_changes(ref="HEAD", start="HEAD", working_tree=True)
            ```
        """
        if start is None:
            revspec = f"{remote_name}...{ref}" if merge_base else f"{ref}^!"
        elif merge_base:
            revspec = f"{start}...{ref}"
        else:
            revspec = f"{start}..{ref}"

        patches = [self._get_patch(revspec)]

        if working_tree:
            patches.append(self._get_working_tree_patch())

        # Filter out any empty patches
        patches = [patch.strip() for patch in patches if patch.strip()]

        return ChangeSet.generate_from_diff_output(patches)

    def _get_working_tree_patch(self) -> str:
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
            return self._get_patch("HEAD", env=temp_env)
