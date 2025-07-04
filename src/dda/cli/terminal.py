# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING, Any

import click
from rich.console import Console
from rich.text import Text

from dda.config.constants import Verbosity

if TYPE_CHECKING:
    from rich.status import Status
    from rich.style import Style
    from rich.table import Table

    from dda.config.model.terminal import TerminalConfig


class Terminal:
    def __init__(self, *, config: TerminalConfig, enable_color: bool | None, interactive: bool | None):
        # Force consistent output for test assertions
        self.testing = "DDA_SELF_TESTING" in os.environ

        self.console = Console(
            force_terminal=enable_color,
            force_interactive=interactive,
            no_color=enable_color is False,
            markup=False,
            emoji=False,
            highlight=False,
            legacy_windows=False if self.testing else None,
        )
        self.__config = config

    def display(self, text: str = "", **kwargs: Any) -> None:
        """
        Output text to stdout using the [`info`][dda.config.model.terminal.TerminalStyles.info] style
        regardless of the configured verbosity level.

        Parameters:
            text: The text to output.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`Console.print`][rich.console.Console.print] method.
        """
        self.console.print(text, style=self.__style_info, overflow="ignore", no_wrap=True, crop=False, **kwargs)

    def display_critical(self, text: str = "", **kwargs: Any) -> None:
        """
        Output text to stderr using the [`error`][dda.config.model.terminal.TerminalStyles.error] style
        regardless of the configured verbosity level.

        Parameters:
            text: The text to output.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`Console.print`][rich.console.Console.print] method.
        """
        self.console.stderr = True
        try:
            self.console.print(text, style=self.__style_error, overflow="ignore", no_wrap=True, crop=False, **kwargs)
        finally:
            self.console.stderr = False

    def display_error(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        """
        Output text using the [`error`][dda.config.model.terminal.TerminalStyles.error] style if the
        configured verbosity level is at least [`Verbosity.ERROR`][dda.config.constants.Verbosity.ERROR].

        Parameters:
            text: The text to output.
            stderr: Whether to output to stderr.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`Console.print`][rich.console.Console.print] method.
        """
        if self.__config.verbosity < Verbosity.ERROR:
            return

        self.output(text, style=self.__style_error, stderr=stderr, **kwargs)

    def display_warning(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        """
        Output text using the [`warning`][dda.config.model.terminal.TerminalStyles.warning] style if the
        configured verbosity level is at least [`Verbosity.WARNING`][dda.config.constants.Verbosity.WARNING].

        Parameters:
            text: The text to output.
            stderr: Whether to output to stderr.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`Console.print`][rich.console.Console.print] method.
        """
        if self.__config.verbosity < Verbosity.WARNING:
            return

        self.output(text, style=self.__style_warning, stderr=stderr, **kwargs)

    def display_info(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        """
        Output text using the [`info`][dda.config.model.terminal.TerminalStyles.info] style if the
        configured verbosity level is at least [`Verbosity.INFO`][dda.config.constants.Verbosity.INFO].

        Parameters:
            text: The text to output.
            stderr: Whether to output to stderr.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`Console.print`][rich.console.Console.print] method.
        """
        if self.__config.verbosity < Verbosity.INFO:
            return

        self.output(text, style=self.__style_info, stderr=stderr, **kwargs)

    def display_success(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        """
        Output text using the [`success`][dda.config.model.terminal.TerminalStyles.success] style if the
        configured verbosity level is at least [`Verbosity.INFO`][dda.config.constants.Verbosity.INFO].

        Parameters:
            text: The text to output.
            stderr: Whether to output to stderr.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`Console.print`][rich.console.Console.print] method.
        """
        if self.__config.verbosity < Verbosity.INFO:
            return

        self.output(text, style=self.__style_success, stderr=stderr, **kwargs)

    def display_waiting(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        """
        Output text using the [`waiting`][dda.config.model.terminal.TerminalStyles.waiting] style if the
        configured verbosity level is at least [`Verbosity.INFO`][dda.config.constants.Verbosity.INFO].

        Parameters:
            text: The text to output.
            stderr: Whether to output to stderr.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`Console.print`][rich.console.Console.print] method.
        """
        if self.__config.verbosity < Verbosity.INFO:
            return

        self.output(text, style=self.__style_waiting, stderr=stderr, **kwargs)

    def display_debug(
        self,
        text: str = "",
        level: int = Verbosity.VERBOSE,
        *,
        stderr: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Output text using the [`debug`][dda.config.model.terminal.TerminalStyles.debug] style if the
        configured verbosity level is between [`Verbosity.VERBOSE`][dda.config.constants.Verbosity.VERBOSE] and
        [`Verbosity.TRACE`][dda.config.constants.Verbosity.TRACE] (inclusive).

        Parameters:
            text: The text to output.
            level: The verbosity level.
            stderr: Whether to output to stderr.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`Console.print`][rich.console.Console.print] method.
        """
        if not Verbosity.VERBOSE <= level <= Verbosity.TRACE:
            message = "Debug output can only have verbosity levels between 1 and 3 (inclusive)"
            raise ValueError(message)

        if self.__config.verbosity < level:
            return

        self.output(text, style=self.__style_debug, stderr=stderr, **kwargs)

    def style_success(self, text: str) -> Text:
        return Text(text, style=self.__style_success)

    def style_error(self, text: str) -> Text:
        return Text(text, style=self.__style_error)

    def style_warning(self, text: str) -> Text:
        return Text(text, style=self.__style_warning)

    def style_waiting(self, text: str) -> Text:
        return Text(text, style=self.__style_waiting)

    def style_info(self, text: str) -> Text:
        return Text(text, style=self.__style_info)

    def style_debug(self, text: str) -> Text:
        return Text(text, style=self.__style_debug)

    def display_header(self, title: str) -> None:
        """
        Display a horizontal rule with an embedded title using the
        [`success`][dda.config.model.terminal.TerminalStyles.success] style.

        Parameters:
            title: The title to display.
        """
        self.console.rule(Text(title, self.__style_success))

    def display_table(self, data: dict[str, Any]) -> None:
        """
        Display a table with the given data using the
        [`success`][dda.config.model.terminal.TerminalStyles.success] style for the keys.

        The following data:

        ```python
        {
            "key1": {
                "nested1": {
                    "str": "text",
                    "int": 1,
                    "float": 1.0,
                    "bool": True,
                    "list": ["foo", 2, "bar"],
                },
            },
        }
        ```

        would be displayed as:

        ```text
        ┌──────┬─────────────────────────────────────────────┐
        │ key1 │ ┌─────────┬───────────────────────────────┐ │
        │      │ │ nested1 │ ┌───────┬───────────────────┐ │ │
        │      │ │         │ │ str   │ text              │ │ │
        │      │ │         │ │ int   │ 1                 │ │ │
        │      │ │         │ │ float │ 1.0               │ │ │
        │      │ │         │ │ bool  │ True              │ │ │
        │      │ │         │ │ list  │ ['foo', 2, 'bar'] │ │ │
        │      │ │         │ └───────┴───────────────────┘ │ │
        │      │ └─────────┴───────────────────────────────┘ │
        └──────┴─────────────────────────────────────────────┘
        ```

        Parameters:
            data: The data to display.
        """
        self.output(_construct_table(data, key_style=self.__style_success))

    def display_syntax(self, *args: Any, **kwargs: Any) -> None:
        """
        Display a syntax-highlighted block of text.

        Parameters:
            *args: Additional arguments to pass to the [`Syntax`][rich.syntax.Syntax] constructor.
            **kwargs: Additional keyword arguments to pass to the [`Syntax`][rich.syntax.Syntax] constructor.
        """
        from rich.syntax import Syntax

        kwargs.setdefault("background_color", "default" if self.testing else None)
        self.output(Syntax(*args, **kwargs))

    def display_markdown(self, text: str, **kwargs: Any) -> None:
        from rich.markdown import Markdown

        self.output(Markdown(text), **kwargs)

    def status(self, text: str, **kwargs: Any) -> Status:
        """
        Display a status indicator with the
        [configured spinner][dda.config.model.terminal.TerminalStyles.spinner].
        If the session is not interactive, the status indicator will be displayed as a
        [waiting message][dda.cli.application.Application.display_waiting].

        The returned object must be used as a context manager.

        Parameters:
            text: The text to display.
            **kwargs: Additional keyword arguments to pass to the [`Console.status`][rich.console.Console.status] method.
        """
        if not self.console.is_interactive:
            self.display_waiting(text, **kwargs)
        kwargs.setdefault("spinner", self.__style_spinner)
        return self.console.status(self.style_waiting(text), **kwargs)

    def output(self, *args: Any, stderr: bool = False, **kwargs: Any) -> None:
        kwargs.setdefault("overflow", "ignore")
        kwargs.setdefault("no_wrap", True)
        kwargs.setdefault("crop", False)

        if not stderr:
            self.console.print(*args, **kwargs)
        else:
            self.console.stderr = True
            try:
                self.console.print(*args, **kwargs)
            finally:
                self.console.stderr = False

    @staticmethod
    def prompt(*args: Any, **kwargs: Any) -> str:
        """
        Prompt the user for input.

        Parameters:
            *args: Additional arguments to pass to the [`click.prompt`][click.prompt] function.
            **kwargs: Additional keyword arguments to pass to the [`click.prompt`][click.prompt] function.

        Returns:
            The user's input.
        """
        return click.prompt(*args, **kwargs)

    @staticmethod
    def confirm(*args: Any, **kwargs: Any) -> bool:
        """
        Prompt the user for confirmation.

        Parameters:
            *args: Additional arguments to pass to the [`click.confirm`][click.confirm] function.
            **kwargs: Additional keyword arguments to pass to the [`click.confirm`][click.confirm] function.

        Returns:
            Whether the user confirmed the action.
        """
        return click.confirm(*args, **kwargs)

    @cached_property
    def __style_spinner(self) -> str:
        from rich.spinner import Spinner

        try:
            Spinner(self.__config.styles.spinner)
        except KeyError as e:  # no cov
            message = f"Invalid animation definition for `terminal.styles.spinner`: {e}"
            raise ValueError(message) from None

        return self.__config.styles.spinner

    @cached_property
    def __style_debug(self) -> Style:
        return _parse_style("debug", self.__config.styles.debug)

    @cached_property
    def __style_error(self) -> Style:
        return _parse_style("error", self.__config.styles.error)

    @cached_property
    def __style_info(self) -> Style:
        return _parse_style("info", self.__config.styles.info)

    @cached_property
    def __style_success(self) -> Style:
        return _parse_style("success", self.__config.styles.success)

    @cached_property
    def __style_waiting(self) -> Style:
        return _parse_style("waiting", self.__config.styles.waiting)

    @cached_property
    def __style_warning(self) -> Style:
        return _parse_style("warning", self.__config.styles.warning)


def _parse_style(level: str, style: str) -> Style:
    from rich.errors import StyleSyntaxError
    from rich.style import Style

    try:
        return Style.parse(style)
    except StyleSyntaxError as e:  # no cov
        message = f"Invalid style definition for `terminal.styles.{level}`: {e}"
        raise ValueError(message) from None


def _construct_table(data: dict[str, Any], *, key_style: Style) -> Table:
    from rich.table import Table

    table = Table(show_header=False)
    table.add_column(style=key_style)
    table.add_column()

    for key, value in data.items():
        if isinstance(value, dict):
            table.add_row(key, _construct_table(value, key_style=key_style))
        else:
            table.add_row(key, str(value))

    return table
