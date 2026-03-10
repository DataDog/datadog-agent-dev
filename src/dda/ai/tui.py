# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

if TYPE_CHECKING:
    from dda.ai.agent import AgentSession

_PHASE_STYLE = {
    "created": "dim",
    "running": "cyan",
    "awaiting_pr_confirm": "yellow",
    "monitoring_ci": "blue",
    "awaiting_ci_fix_confirm": "yellow",
    "done": "green",
    "failed": "red",
    "cancelled": "dim red",
}

_PHASE_SPINNER = {"running", "monitoring_ci"}

_LOG_LINES = 25


class AgentTUI:
    """Rich Live TUI for a single agent session."""

    def __init__(self, session: AgentSession, *, console: Console | None = None):
        self._session = session
        self._console = console or Console()
        self._log_buf: deque[str] = deque(maxlen=_LOG_LINES)
        self._confirm_message: str = ""
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=4,
            transient=False,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._live.start()

    def stop(self) -> None:
        self._live.stop()

    def __enter__(self) -> AgentTUI:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def update_session(self, session: AgentSession) -> None:
        self._session = session
        self._refresh()

    def append_log(self, text: str) -> None:
        for line in text.splitlines():
            if line:
                self._log_buf.append(line)
        self._refresh()

    def set_confirm_prompt(self, message: str) -> None:
        self._confirm_message = message
        self._refresh()

    def clear_confirm_prompt(self) -> None:
        self._confirm_message = ""
        self._refresh()

    def prompt_user(self, message: str) -> str:
        """
        Pause the live renderer and prompt the user for input.
        Returns the user's answer (stripped).
        """
        self._live.stop()
        try:
            self._console.print()
            answer = self._console.input(f"[yellow]⚡ {message}[/yellow] [dim][y/N][/dim] ").strip()
        finally:
            self._live.start()
        return answer

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        self._live.update(self._render())

    def _render(self) -> Group:
        s = self._session
        phase_style = _PHASE_STYLE.get(str(s.phase), "")
        phase_str = str(s.phase).replace("_", " ")

        # Header
        header_parts = [
            Text(f"dda ai", style="bold"),
            Text(f"  agent: {s.id}", style="dim"),
            Text(f"  workspace: {s.workspace}", style="cyan"),
        ]
        if s.branch:
            header_parts.append(Text(f"  branch: {s.branch}", style="magenta"))
        if s.pr_url:
            header_parts.append(Text(f"  PR: {s.pr_url}", style="blue underline"))

        header = Columns(header_parts, padding=(0, 0))

        phase_text = Text()
        if str(s.phase) in _PHASE_SPINNER:
            phase_text.append("⠸ ", style="cyan")
        phase_text.append(phase_str, style=phase_style)

        # Task panel
        task_panel = Panel(
            Text(s.prompt[:200], overflow="fold"),
            title="[bold]TASK[/bold]",
            border_style="dim",
            padding=(0, 1),
        )

        # Log panel
        log_lines = Text(overflow="fold")
        for line in self._log_buf:
            log_lines.append(line + "\n", style="dim")
        log_panel = Panel(
            log_lines,
            title="[bold]CLAUDE OUTPUT[/bold]",
            border_style="dim",
            padding=(0, 1),
        )

        parts: list = [
            Panel(
                Group(header, Text("  phase: ") + phase_text),
                border_style="bold blue",
                padding=(0, 1),
            ),
            task_panel,
            log_panel,
        ]

        if self._confirm_message:
            parts.append(
                Panel(
                    Text(self._confirm_message, style="yellow"),
                    title="[bold yellow]⚡ AWAITING CONFIRMATION[/bold yellow]",
                    border_style="yellow",
                    padding=(0, 1),
                )
            )

        return Group(*parts)
