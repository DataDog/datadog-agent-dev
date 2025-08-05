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


def test_existing(dda, temp_dir, mocker):
    mock = mocker.patch("click.launch")
    mocker.patch("dda.env.qa.types.linux_container.LinuxContainer.start")
    mocker.patch(
        "dda.env.qa.types.linux_container.LinuxContainer.status",
        return_value=EnvironmentStatus(state=EnvironmentState.STOPPED),
    )
    agent_config_dir = temp_dir / "data" / "env" / "qa" / "linux-container" / "default" / ".state" / "agent_config"

    result = dda("env", "qa", "start")
    assert result.exit_code == 0, result.output
    assert not result.output

    result = dda("env", "qa", "config", "explore")

    assert result.exit_code == 0, result.output
    assert not result.output
    mock.assert_called_once_with(str(agent_config_dir / "datadog.yaml"), locate=True)


def test_not_found(dda, helpers):
    result = dda("env", "qa", "config", "explore")

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        """
        QA environment `default` of type `linux-container` does not exist
        """
    )
