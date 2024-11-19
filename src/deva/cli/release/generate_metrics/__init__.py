# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click
from datetime import datetime

from deva.cli.base import dynamic_command

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(short_help="Generate metrics for the agent release")
@click.argument("milestone", required=True)
@click.argument("freeze_date", required=True)
@click.argument("release_date", required=True)
@click.pass_obj
def cmd(app: Application, milestone, freeze_date, release_date) -> None:
    print("Generating metrics for the agent release")

    # 1. Calculate the lead time for changes data
    lead_time = get_release_lead_time(freeze_date, release_date)
    print("Lead Time for Changes data")
    print("--------------------------")
    print(lead_time)

    # Step 2: Agent stability data
    print("\n")
    print("Agent stability data")
    print("--------------------")
    print("To be implemented")

    # 3. Code changes
    git_log = app.subprocess.capture(f"git log --shortstat {milestone}-devel..{milestone}")
    after_grep = app.subprocess.capture("grep \"files changed\"", input=git_log)
    after_awk = app.subprocess.capture("awk '{{files+=$1; inserted+=$4; deleted+=$6}} END {{print files,\",\", inserted,\",\", deleted}}'", input=after_grep)

    print("\n")
    print("Code changes")
    print("------------")
    print(after_awk)

def get_release_lead_time(freeze_date, release_date):
    release_date = datetime.strptime(release_date, "%Y-%m-%d")
    freeze_date = datetime.strptime(freeze_date, "%Y-%m-%d")

    return (release_date - freeze_date).days