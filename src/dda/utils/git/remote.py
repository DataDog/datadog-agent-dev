# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ada_url import URL


class Remote:
    def __init__(self, url: str) -> None:
        self.__raw_url = url

    @property
    def url(self) -> str:
        """
        The URL of the remote.
        """
        return self.__raw_url

    @cached_property
    def protocol(self) -> str:
        """
        The protocol of the remote.
        """
        # Remove trailing colon
        return self.__url.protocol[:-1]

    @cached_property
    def hostname(self) -> str | None:
        """
        The hostname of the remote.
        """
        return self.__url.hostname

    @cached_property
    def port(self) -> int | None:
        """
        The port of the remote, or None if not specified.
        """
        return int(self.__url.port) if self.__url.port else None

    @cached_property
    def username(self) -> str | None:
        """
        The username of the remote, or None if not specified.
        """
        return self.__url.username or None

    @cached_property
    def org(self) -> str:
        """
        The name of the organization the remote belongs to.
        """
        return self.full_repo.split("/")[0]

    @cached_property
    def repo(self) -> str:
        """
        The name of the repository.
        """
        return self.full_repo.split("/")[-1]

    @cached_property
    def full_repo(self) -> str:
        return "" if self.__url.pathname == "/" else self.__url.pathname[1:].removesuffix(".git")

    @cached_property
    def __url(self) -> URL:
        from ada_url import URL

        try:
            return URL(self.__raw_url)
        except ValueError:
            # SCP-style SSH
            return URL(f"ssh://{self.__raw_url.replace(':', '/', 1)}")
