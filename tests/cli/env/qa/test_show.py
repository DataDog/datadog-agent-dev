# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from subprocess import CompletedProcess

import msgspec
import pytest

from dda.env.qa.types.linux_container import LinuxContainerConfig

pytestmark = [pytest.mark.usefixtures("private_storage")]


def test_empty_env_dir(dda, helpers):
    result = dda("env", "qa", "show")
    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            """
            No QA environments found
            """
        ),
    )


def test_empty_instance_dirs(dda, helpers, temp_dir):
    root_dir = temp_dir / "data" / "env" / "qa" / "linux-container"
    instance_dir = root_dir / "foo"
    instance_dir.ensure_dir()

    result = dda("env", "qa", "show")
    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            """
            No QA environments found
            """
        ),
    )


def test_default(dda, helpers, temp_dir):
    root_dir = temp_dir / "data" / "env" / "qa" / "linux-container"
    instance_foo_dir = root_dir / "foobar" / ".state"
    instance_foo_dir.ensure_dir()
    (instance_foo_dir / "config.json").write_bytes(msgspec.json.encode(LinuxContainerConfig()))

    instance_bar_dir = root_dir / "baz" / ".state"
    instance_bar_dir.ensure_dir()
    (instance_bar_dir / "config.json").write_bytes(msgspec.json.encode(LinuxContainerConfig(env={"FOO": "BAR"})))

    with helpers.hybrid_patch(
        "subprocess.run",
        return_values={
            # Show that the first instance is started
            1: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "running"}}])),
            # Show that the second instance is stopped
            2: CompletedProcess([], returncode=0, stdout=json.dumps([{"State": {"Status": "created"}}])),
        },
    ):
        result = dda("env", "qa", "show")

    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            ┌─────────────────┬─────────────────────────────────────────────────────┐
            │ linux-container │ ┌────────┬────────────────────────────────────────┐ │
            │                 │ │ baz    │ ┌────────┬───────────────────────────┐ │ │
            │                 │ │        │ │ State  │ started                   │ │ │
            │                 │ │        │ │ Config │ ┌───────┬───────────────┐ │ │ │
            │                 │ │        │ │        │ │ image │ datadog/agent │ │ │ │
            │                 │ │        │ │        │ │ pull  │ False         │ │ │ │
            │                 │ │        │ │        │ │ cli   │ docker        │ │ │ │
            │                 │ │        │ │        │ │ env   │ ┌─────┬─────┐ │ │ │ │
            │                 │ │        │ │        │ │       │ │ FOO │ BAR │ │ │ │ │
            │                 │ │        │ │        │ │       │ └─────┴─────┘ │ │ │ │
            │                 │ │        │ │        │ │ e2e   │ False         │ │ │ │
            │                 │ │        │ │        │ └───────┴───────────────┘ │ │ │
            │                 │ │        │ └────────┴───────────────────────────┘ │ │
            │                 │ │ foobar │ ┌────────┬───────────────────────────┐ │ │
            │                 │ │        │ │ State  │ stopped                   │ │ │
            │                 │ │        │ │ Config │ ┌───────┬───────────────┐ │ │ │
            │                 │ │        │ │        │ │ image │ datadog/agent │ │ │ │
            │                 │ │        │ │        │ │ pull  │ False         │ │ │ │
            │                 │ │        │ │        │ │ cli   │ docker        │ │ │ │
            │                 │ │        │ │        │ │ e2e   │ False         │ │ │ │
            │                 │ │        │ │        │ └───────┴───────────────┘ │ │ │
            │                 │ │        │ └────────┴───────────────────────────┘ │ │
            │                 │ └────────┴────────────────────────────────────────┘ │
            └─────────────────┴─────────────────────────────────────────────────────┘
            """
        ),
    )
