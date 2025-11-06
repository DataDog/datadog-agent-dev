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


def test_existing(dda, helpers, temp_dir, mocker):
    mocker.patch("dda.env.qa.types.linux_container.LinuxContainer.start")
    mocker.patch(
        "dda.env.qa.types.linux_container.LinuxContainer.status",
        return_value=EnvironmentStatus(state=EnvironmentState.STOPPED),
    )
    agent_config_dir = temp_dir / "data" / "env" / "qa" / "linux-container" / "default" / ".state" / "agent_config"

    result = dda("env", "qa", "start")
    result.check_exit_code(0)

    result = dda("env", "qa", "config", "find")
    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            {agent_config_dir}
            """
        ),
    )


def test_not_found(dda, helpers):
    result = dda("env", "qa", "config", "find")
    result.check(
        exit_code=1,
        output=helpers.dedent(
            """
            QA environment `default` of type `linux-container` does not exist
            """
        ),
    )
