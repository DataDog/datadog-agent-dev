# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
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

    def __init__(self, session: AgentSession):
        self._session = session
        # Always use a dedicated console — never inherit app.console which has
        # markup=False and other constraints that break Rich Live rendering.
        self._console = Console()
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

    def show_changes_and_prompt(self, commits: str, diff: str, message: str) -> str:
        """
        Stop the live renderer, display git commits and diff, then ask for
        confirmation.  Returns the user's answer (stripped).
        """
        from rich.panel import Panel
        from rich.syntax import Syntax

        self._live.stop()
        try:
            if commits.strip():
                self._console.print(
                    Panel(commits.strip(), title="[bold magenta]COMMITS[/bold magenta]", border_style="magenta")
                )
            if diff.strip():
                self._console.print(
                    Panel(
                        Syntax(diff, "diff", theme="monokai", word_wrap=True),
                        title="[bold magenta]CHANGES[/bold magenta]",
                        border_style="magenta",
                    )
                )
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

        # Header — one panel: meta + phase + task summary
        phase_text = Text()
        if str(s.phase) in _PHASE_SPINNER:
            phase_text.append("⠸ ", style="cyan")
        phase_text.append(phase_str, style=phase_style)

        meta = Text()
        meta.append("dda ai", style="bold")
        meta.append(f"  agent: {s.id}", style="dim")
        meta.append(f"  workspace: {s.workspace}", style="cyan")
        if s.branch:
            meta.append(f"  branch: {s.branch}", style="magenta")
        if s.pr_url:
            meta.append(f"  PR: {s.pr_url}", style="blue underline")
        meta.append("  phase: ")
        meta.append_text(phase_text)
        meta.append(f"\n  task: {s.prompt[:120]}", style="dim")

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
            Panel(meta, border_style="bold blue", padding=(0, 1)),
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
