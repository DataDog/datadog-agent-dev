# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field

from dda.config.constants import Verbosity


class TerminalStyles(Struct, frozen=True, forbid_unknown_fields=True):
    """
    Styling documentation:

    - [Syntax](https://rich.readthedocs.io/en/stable/style.html)
    - [Standard colors](https://rich.readthedocs.io/en/stable/appendix/colors.html)

    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [terminal.styles]
    error = "bold red"
    warning = "bold yellow"
    info = "bold"
    success = "bold cyan"
    waiting = "bold magenta"
    debug = "bold on bright_black"
    spinner = "simpleDotsScrolling"
    ```
    ///
    """

    error: str = "bold red"
    warning: str = "bold yellow"
    info: str = "bold"
    success: str = "bold cyan"
    waiting: str = "bold magenta"
    debug: str = "bold on bright_black"
    spinner: str = "simpleDotsScrolling"
    """
    The list of available spinners can be found [here](https://github.com/Textualize/rich/blob/master/rich/_spinners.py).
    """


class TerminalConfig(Struct, frozen=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [terminal]
    verbosity = 0
    ```
    ///
    """

    verbosity: Verbosity = Verbosity.INFO
    styles: TerminalStyles = field(default_factory=TerminalStyles)
