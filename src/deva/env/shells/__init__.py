# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from deva.env.shells.interface import Shell


def get_shell(name: str) -> type[Shell]:
    shell = __SHELLS.get(name)
    if shell is None:
        message = f"Unknown shell: {name}"
        raise ValueError(message)

    return shell()


def __get_bash() -> type[Shell]:
    from deva.env.shells.bash import BashShell

    return BashShell


def __get_zsh() -> type[Shell]:
    from deva.env.shells.zsh import ZshShell

    return ZshShell


def __get_nu() -> type[Shell]:
    from deva.env.shells.nu import NuShell

    return NuShell


__SHELLS: dict[str, Callable[[], type[Shell]]] = {
    "bash": __get_bash,
    "nu": __get_nu,
    "zsh": __get_zsh,
}
