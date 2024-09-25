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

from deva.config.constants import Verbosity

if TYPE_CHECKING:
    from rich.status import Status
    from rich.style import Style

    from deva.config.model.terminal import TerminalConfig


class Terminal:
    def __init__(self, *, config: TerminalConfig, enable_color: bool | None, interactive: bool | None):
        # Force consistent output for test assertions
        self.testing = "DEVA_SELF_TESTING" in os.environ

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
        self.console.print(text, style=self.__style_info, overflow="ignore", no_wrap=True, crop=False, **kwargs)

    def display_critical(self, text: str = "", **kwargs: Any) -> None:
        self.console.stderr = True
        try:
            self.console.print(text, style=self.__style_error, overflow="ignore", no_wrap=True, crop=False, **kwargs)
        finally:
            self.console.stderr = False

    def display_error(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        if self.__config.verbosity < Verbosity.ERROR:
            return

        self.output(text, style=self.__style_error, stderr=stderr, **kwargs)

    def display_warning(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        if self.__config.verbosity < Verbosity.WARNING:
            return

        self.output(text, style=self.__style_warning, stderr=stderr, **kwargs)

    def display_info(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        if self.__config.verbosity < Verbosity.INFO:
            return

        self.output(text, style=self.__style_info, stderr=stderr, **kwargs)

    def display_success(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        if self.__config.verbosity < Verbosity.INFO:
            return

        self.output(text, style=self.__style_success, stderr=stderr, **kwargs)

    def display_waiting(self, text: str = "", *, stderr: bool = True, **kwargs: Any) -> None:
        if self.__config.verbosity < Verbosity.INFO:
            return

        self.output(text, style=self.__style_waiting, stderr=stderr, **kwargs)

    def display_debug(self, text: str = "", level: int = 1, *, stderr: bool = True, **kwargs: Any) -> None:
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
        self.console.rule(Text(title, self.__style_success))

    def display_syntax(self, *args: Any, **kwargs: Any) -> None:
        from rich.syntax import Syntax

        kwargs.setdefault("background_color", "default" if self.testing else None)
        self.output(Syntax(*args, **kwargs))

    def status(self, *args: Any, **kwargs: Any) -> Status:
        kwargs.setdefault("spinner", self.__style_spinner)
        return self.console.status(*args, **kwargs)

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
    def prompt(text: str, **kwargs: Any) -> Any:
        return click.prompt(text, **kwargs)

    @staticmethod
    def confirm(text: str, **kwargs: Any) -> bool:
        return click.confirm(text, **kwargs)

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
