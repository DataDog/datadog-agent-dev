# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import ClassVar, Literal


class Remote(ABC):
    protocol: ClassVar[Literal["https", "git"]]

    @classmethod
    def from_url(cls, url: str) -> Remote:
        if url.startswith("https://"):
            return HTTPSRemote(url)
        if url.startswith("git@"):
            return SSHRemote(url)
        msg = f"Invalid protocol: {url}"
        raise ValueError(msg)

    def __init__(self, url: str) -> None:
        self.url = url

    @property
    @abstractmethod
    def org(self) -> str:
        """
        The name of the organization the remote belongs to.
        """

    @property
    @abstractmethod
    def repo(self) -> str:
        """
        The name of the repository.
        """

    @cached_property
    def full_repo(self) -> str:
        return f"{self.org}/{self.repo}"


class HTTPSRemote(Remote):
    protocol: ClassVar[Literal["https"]] = "https"

    @cached_property
    def org(self) -> str:
        return self.url.split("/")[3]

    @cached_property
    def repo(self) -> str:
        return self.url.removesuffix(".git").rsplit("/", 1)[-1]


class SSHRemote(Remote):
    protocol: ClassVar[Literal["git"]] = "git"

    @cached_property
    def org(self) -> str:
        return self.url.split(":")[1].split("/")[0]

    @cached_property
    def repo(self) -> str:
        return self.url.split(":")[1].split("/")[-1].removesuffix(".git")
