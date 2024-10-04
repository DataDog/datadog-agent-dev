# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field

from deva.config.constants import Verbosity


class TerminalStyles(Struct, frozen=True, forbid_unknown_fields=True):
    # https://rich.readthedocs.io/en/latest/style.html
    # https://rich.readthedocs.io/en/latest/appendix/colors.html
    error: str = "bold red"
    warning: str = "bold yellow"
    info: str = "bold"
    success: str = "bold cyan"
    waiting: str = "bold magenta"
    debug: str = "bold on bright_black"
    # https://github.com/Textualize/rich/blob/master/rich/_spinners.py
    spinner: str = "simpleDotsScrolling"


class TerminalConfig(Struct, frozen=True):
    verbosity: Verbosity = Verbosity.INFO
    styles: TerminalStyles = field(default_factory=TerminalStyles)
