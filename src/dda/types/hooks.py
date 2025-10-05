# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from msgspec import Struct

if TYPE_CHECKING:
    from collections.abc import Callable


class Hooks(Struct, frozen=True):
    encode: Callable[[Any], Any]
    decode: Callable[[Any], Any]


def register_hooks(
    typ: type[Any],
    *,
    encode: Callable[[Any], Any],
    decode: Callable[[Any], Any],
) -> None:
    __HOOKS[typ] = Hooks(encode=encode, decode=decode)


def enc_hook(obj: Any) -> Any:
    if (registered_type := __HOOKS.get(type(obj))) is not None:
        return registered_type.encode(obj)

    message = f"Cannot encode: {obj!r}"
    raise NotImplementedError(message)


def dec_hook(typ: type[Any], obj: Any) -> Any:
    if (registered_type := __HOOKS.get(typ)) is not None:
        return registered_type.decode(obj)

    message = f"Cannot decode: {obj!r}"
    raise ValueError(message)


__HOOKS: dict[type[Any], Hooks] = {}

register_hooks(MappingProxyType, encode=dict, decode=MappingProxyType)
