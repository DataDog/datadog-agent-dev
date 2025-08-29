# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self


class SHA1Hash(str):
    """
    A hexadecimal representation of a SHA-1 hash.
    """

    LENGTH = 40
    __slots__ = ()

    def __new__(cls, value: str) -> Self:
        if len(value) != cls.LENGTH or any(c not in "0123456789abcdef" for c in value.lower()):
            msg = f"Invalid SHA-1 hash: {value}"
            raise ValueError(msg)
        return str.__new__(cls, value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    def __bytes__(self) -> bytes:
        return bytes.fromhex(self)
