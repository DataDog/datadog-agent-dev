# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property

AVAILABLE_PROTOCOLS = ("ssh", "rsync", "http", "https", "git", "file")


class Remote(ABC):
    @classmethod
    def from_url(cls, url: str) -> Remote:
        if url.startswith(tuple(f"{protocol}://" for protocol in AVAILABLE_PROTOCOLS)):
            return URIStyleRemote(url)
        if "@" in url and ":" in url:
            return RCPStyleRemote(url)

        msg = f"Invalid URL: {url}"
        raise ValueError(msg)

    def __init__(self, url: str) -> None:
        self.url = url

    @property
    @abstractmethod
    def protocol(self) -> str:
        """
        The protocol of the remote.
        """

    @property
    @abstractmethod
    def authority(self) -> str:
        """
        The authority of the remote. Includes username and port if present, under the form <username>@<host>:<port>.
        """

    @property
    @abstractmethod
    def path(self) -> str:
        """
        The repository path on the remote, excluding an eventual `.git` suffix.
        """

    @cached_property
    def port(self) -> int | None:
        """
        The port of the remote. Returns None if not specified, in which case the default port for the protocol is used.
        """
        return int(self.authority.split(":")[1]) if ":" in self.authority else None

    @cached_property
    def username(self) -> str | None:
        """
        The username of the remote. Returns None if not specified.
        """
        return self.authority.split("@")[0] if "@" in self.authority else None

    @cached_property
    def host(self) -> str | None:
        """
        The host of the remote.
        """
        prefix = self.username + "@" if self.username else ""
        suffix = ":" + str(self.port) if self.port else ""
        return self.authority.removeprefix(prefix).removesuffix(suffix)

    def _get_org_and_repo(self) -> tuple[str, str]:
        parts = self.path.split("/")
        if len(parts) != 2:  # noqa: PLR2004
            msg = f"Repo path is not under the form org/repo: {self.path}"
            raise ValueError(msg)
        return parts[0], parts[1]

    @cached_property
    def org(self) -> str:
        """
        The name of the organization the remote belongs to.
        """
        return self._get_org_and_repo()[0]

    @cached_property
    def repo(self) -> str:
        """
        The name of the repository.
        """
        return self._get_org_and_repo()[1]

    @cached_property
    def full_repo(self) -> str:
        return f"{self.org}/{self.repo}"


# See: https://stackoverflow.com/questions/70295093/git-uris-does-not-match-ssh-uri-specification?rq=3
class URIStyleRemote(Remote):
    # Format: <protocol>://<some host>/<some path>(.git)
    @cached_property
    def protocol(self) -> str:
        return self.url.split("://")[0]

    @cached_property
    def authority(self) -> str:
        return self.url.split("://")[1].split("/")[0]

    @cached_property
    def path(self) -> str:
        return (
            self.url.removeprefix(f"{self.protocol}://")
            .removeprefix(self.authority)
            .removeprefix("/")
            .removesuffix(".git")
        )


class RCPStyleRemote(Remote):
    # Format: <username>@<host>:<some path>(.git)
    # Port cannot be specified, and the username is always present.
    # The protocol is always SSH.
    @cached_property
    def protocol(self) -> str:
        return "ssh"

    @cached_property
    def authority(self) -> str:
        return self.url.split(":")[0]

    @cached_property
    def path(self) -> str:
        return self.url.split(":")[1].removesuffix(".git")
