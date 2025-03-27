# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.utils.ssh import derive_dynamic_ssh_port, ssh_base_command


@pytest.mark.parametrize("port", [pytest.param(22, id="int port"), pytest.param("22", id="str port")])
def test_ssh_base_command(port: int | str) -> None:
    assert ssh_base_command("host", port) == ["ssh", "-A", "-q", "-t", "-p", str(port), "host", "--"]


def test_derive_dynamic_ssh_port() -> None:
    assert 49152 <= derive_dynamic_ssh_port("key") <= 65535


# https://github.com/pytest-dev/pyfakefs/issues/1086
# @pytest.mark.usefixtures("fs")
# def test_write_server_config() -> None:
#     hostname = "localhost"
#     write_server_config(hostname, {"foo": "bar", "baz": "qux"})

#     config_file = Path.home() / ".ssh" / ".dda" / hostname
#     assert config_file.is_file()
