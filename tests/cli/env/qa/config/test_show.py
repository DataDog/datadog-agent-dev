# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys

import pytest

from dda.env.models import EnvironmentState, EnvironmentStatus

pytestmark = [pytest.mark.usefixtures("private_storage")]


@pytest.fixture(autouse=True)
def _updated_config(config_file):
    # TODO: Remove once the default Windows QA environment is implemented
    if sys.platform == "win32":
        config_file.data["env"] = {"qa": {"default-type": "linux-container"}}
        config_file.save()


def test_not_found(dda, helpers):
    result = dda("env", "qa", "config", "show")
    result.check(
        exit_code=1,
        output=helpers.dedent(
            """
            QA environment `default` of type `linux-container` does not exist
            """
        ),
    )


def test_default(dda, helpers, temp_dir, mocker):
    mocker.patch("dda.env.qa.types.linux_container.LinuxContainer.start")
    mocker.patch(
        "dda.env.qa.types.linux_container.LinuxContainer.status",
        return_value=EnvironmentStatus(state=EnvironmentState.STOPPED),
    )

    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "default"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").write_text(
        helpers.dedent(
            """
            api_key: foo
            bar: baz
            """
        )
    )

    result = dda("env", "qa", "start")
    result.check_exit_code(0)

    result = dda("env", "qa", "config", "show")
    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            ┌────────┬─────────────────────┐
            │ Config │ ┌─────────┬───────┐ │
            │        │ │ api_key │ ***** │ │
            │        │ │ bar     │ baz   │ │
            │        │ └─────────┴───────┘ │
            └────────┴─────────────────────┘
            """
        ),
    )


def test_modified(dda, helpers, temp_dir, mocker, config_file):
    mocker.patch("dda.env.qa.types.linux_container.LinuxContainer.start")
    mocker.patch(
        "dda.env.qa.types.linux_container.LinuxContainer.status",
        return_value=EnvironmentStatus(state=EnvironmentState.STOPPED),
    )

    config_file.data["orgs"]["foo"] = {"app_key": "bar", "site": "datadoghq.com"}
    config_file.save()

    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "default"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").write_text(
        helpers.dedent(
            """
            api_key: foo
            bar: baz
            """
        )
    )

    result = dda("env", "qa", "start")
    result.check_exit_code(0)

    agent_config_dir = temp_dir / "data" / "env" / "qa" / "linux-container" / "default" / ".state" / "agent_config"
    agent_config_file = agent_config_dir / "datadog.yaml"
    agent_config_file.write_text(f"{agent_config_file.read_text()}\ninherit_org: foo")

    result = dda("env", "qa", "config", "show")
    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            ┌────────┬─────────────────────────────┐
            │ Config │ ┌─────────┬───────────────┐ │
            │        │ │ api_key │ *****         │ │
            │        │ │ app_key │ *****         │ │
            │        │ │ bar     │ baz           │ │
            │        │ │ site    │ datadoghq.com │ │
            │        │ └─────────┴───────────────┘ │
            └────────┴─────────────────────────────┘
            """
        ),
    )
