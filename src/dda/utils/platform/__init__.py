# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import contextlib
import os
import platform
import sys
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID


if sys.platform == "win32":
    __PLATFORM_ID = "windows"
    __PLATFORM_NAME = "Windows"
    __DEFAULT_SHELL = os.environ.get("SHELL", os.environ.get("COMSPEC", "cmd"))

    def __join_command_args(args: list[str]) -> str:
        import subprocess

        return subprocess.list2cmdline(args)

    def __get_machine_id() -> UUID | None:
        import winreg
        from uuid import UUID

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return UUID(value)


elif sys.platform == "darwin":
    __PLATFORM_ID = "macos"
    __PLATFORM_NAME = "macOS"
    __DEFAULT_SHELL = os.environ.get("SHELL", "zsh")

    def __join_command_args(args: list[str]) -> str:
        import shlex

        return shlex.join(args)

    def __get_machine_id() -> UUID | None:
        import re
        import subprocess
        from uuid import UUID

        process = subprocess.run(
            ["ioreg", "-c", "IOPlatformExpertDevice", "-d2"],  # noqa: S607
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )
        match = re.search(rb'"IOPlatformUUID"\s*=\s*"([^"]+)"', process.stdout)
        return UUID(match.group(1).decode("utf-8")) if match else None

else:
    __PLATFORM_ID = "linux"
    __PLATFORM_NAME = "Linux"
    __DEFAULT_SHELL = os.environ.get("SHELL", "bash")

    def __join_command_args(args: list[str]) -> str:
        import shlex

        return shlex.join(args)

    def __get_machine_id() -> UUID | None:
        from uuid import UUID

        for path in (
            # https://utcc.utoronto.ca/~cks/space/blog/linux/DMIDataInSysfs
            # Section 7.2.1 of https://www.dmtf.org/sites/default/files/standards/documents/DSP0134_3.0.0.pdf
            # https://github.com/torvalds/linux/blob/v6.14/drivers/firmware/dmi-id.c#L50
            # https://cloud.google.com/compute/docs/instances/get-uuid#linux
            "/sys/class/dmi/id/product_uuid",
            # https://www.freedesktop.org/software/systemd/man/latest/machine-id.html
            "/etc/machine-id",
            # https://wiki.debian.org/MachineId
            "/var/lib/dbus/machine-id",
        ):
            with contextlib.suppress(Exception), open(path, encoding="utf-8") as f:
                return UUID(f.read().strip())

        return None


PLATFORM_ID = __PLATFORM_ID
"""
A short identifier for the current platform. Known values:

- `linux`
- `windows`
- `macos`
"""
PLATFORM_NAME = __PLATFORM_NAME
"""
The human readable name of the current platform. Known values:

- Linux
- Windows
- macOS
"""
DEFAULT_SHELL = __DEFAULT_SHELL
"""
The default shell for the current platform. Values are taken from environment variables, with
platform-specific fallbacks.

Platform | Environment variables | Fallback
--- | --- | ---
`linux` | `SHELL` | `bash`
`windows` | `SHELL`, `COMSPEC` | `cmd`
`macos` | `SHELL` | `zsh`
"""


def which(name: str) -> str | None:
    """
    This is equivalent to [shutil.which][] except on Windows, where extensions will no longer be entirely capitalized.
    """
    import shutil

    path = shutil.which(name)
    if path is None:
        return None

    if PLATFORM_ID != "windows":
        return path

    root, ext = os.path.splitext(path)
    return f"{root}{ext.lower()}"


def join_command_args(args: list[str]) -> str:
    """
    Create a valid shell command from a list of arguments.

    Parameters:
        args: A list of command line arguments.

    Returns:
        A single string of command line arguments.
    """
    return __join_command_args(args)


@cache
def get_machine_id() -> UUID:
    """
    Get a unique identifier for the current machine that is consistent across reboots and different
    processes. The following platform-specific methods are given priority:

    Platform | Method
    --- | ---
    `linux` | The [`/sys/class/dmi/id/product_uuid`](https://utcc.utoronto.ca/~cks/space/blog/linux/DMIDataInSysfs), [`/etc/machine-id`](https://www.freedesktop.org/software/systemd/man/latest/machine-id.html) or `/var/lib/dbus/machine-id` files
    `windows` | The `HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid` registry key
    `macos` | The [`IOPlatformUUID`](https://developer.apple.com/documentation/iokit/kioplatformuuidkey/) property of the [`IOPlatformExpertDevice`](https://developer.apple.com/library/archive/technotes/tn1103/_index.html) node in the [I/O Registry](https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/TheRegistry/TheRegistry.html#//apple_ref/doc/uid/TP0000014-TP9)

    As a fallback, the ID will be generated using the MAC address.
    """
    machine_id: UUID | None = None
    with contextlib.suppress(Exception):
        machine_id = __get_machine_id()

    if machine_id is not None:
        return machine_id

    import uuid

    return uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid.getnode()))


if sys.platform == "win32":

    def get_os_name() -> str:
        return f"{platform.system()} {platform.win32_ver()[0]} {platform.win32_edition()}"

    def get_os_version() -> str:
        return platform.win32_ver()[0]

elif sys.platform == "darwin":

    def get_os_name() -> str:
        return f"{platform.system()} {platform.mac_ver()[0]}"

    def get_os_version() -> str:
        return platform.mac_ver()[0]

else:

    def get_os_name() -> str:
        return platform.freedesktop_os_release()["NAME"]

    def get_os_version() -> str:
        return platform.freedesktop_os_release()["VERSION_ID"]
