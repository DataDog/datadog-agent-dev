# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.cli.base import dynamic_group


@dynamic_group(
    short_help="Orchestrate AI coding agents on workspaces",
)
def cmd() -> None:
    """
    Orchestrate Claude AI coding agents running on remote Datadog workspaces.

    Agents receive a task (prompt, plan file, or Jira ticket), write code, and
    guide it through code review, PR creation, and CI until the branch is green.
    """
