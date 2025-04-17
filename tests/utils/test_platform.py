# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os

import pytest

from dda.utils import platform


@pytest.mark.requires_windows
class TestWindows:
    def test_id(self):
        assert platform.PLATFORM_ID == "windows"

    def test_name(self):
        assert platform.PLATFORM_NAME == "Windows"

    def test_default_shell(self):
        expected_shell = os.environ.get("SHELL", os.environ.get("COMSPEC", "cmd"))
        assert platform.DEFAULT_SHELL == expected_shell  # noqa: SIM300


@pytest.mark.requires_macos
class TestMacOS:
    def test_id(self):
        assert platform.PLATFORM_ID == "macos"

    def test_name(self):
        assert platform.PLATFORM_NAME == "macOS"

    def test_default_shell(self):
        expected_shell = os.environ.get("SHELL", "zsh")
        assert platform.DEFAULT_SHELL == expected_shell  # noqa: SIM300


@pytest.mark.requires_linux
class TestLinux:
    def test_id(self):
        assert platform.PLATFORM_ID == "linux"

    def test_name(self):
        assert platform.PLATFORM_NAME == "Linux"

    def test_default_shell(self):
        expected_shell = os.environ.get("SHELL", "bash")
        assert platform.DEFAULT_SHELL == expected_shell  # noqa: SIM300


class TestMachineId:
    def test_platform_specific(self):
        machine_id = str(platform.get_machine_id())
        assert str(platform.get_machine_id()) == machine_id

        parts = machine_id.split("-")
        lengths = list(map(len, parts))
        assert lengths == [8, 4, 4, 4, 12]

    def test_fallback(self, mocker):
        mocker.patch("dda.utils.platform.__get_machine_id", return_value=None)

        platform.get_machine_id.cache_clear()
        machine_id = str(platform.get_machine_id())
        platform.get_machine_id.cache_clear()
        assert str(platform.get_machine_id()) == machine_id

        parts = machine_id.split("-")
        lengths = list(map(len, parts))
        assert lengths == [8, 4, 4, 4, 12]
