# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from dda.env.dev.interface import DeveloperEnvironmentInterface
    from dda.env.dev.types.linux_container import LinuxContainer


DEFAULT_DEV_ENV = "windows-container" if sys.platform == "win32" else "linux-container"


def get_dev_env(env_type: str) -> type[DeveloperEnvironmentInterface]:
    getter = __DEV_ENVS.get(env_type)
    if getter is None:
        message = f"Unknown developer environment: {env_type}"
        raise ValueError(message)

    return getter()


def __get_windows_container() -> type[DeveloperEnvironmentInterface]:
    raise NotImplementedError


def __get_windows_cloud() -> type[DeveloperEnvironmentInterface]:
    raise NotImplementedError


def __get_linux_container() -> type[LinuxContainer]:
    from dda.env.dev.types.linux_container import LinuxContainer

    return LinuxContainer


if sys.platform == "win32":
    __DEV_ENVS: dict[str, Callable[[], type[DeveloperEnvironmentInterface[Any]]]] = {
        "windows-container": __get_windows_container,
        "windows-cloud": __get_windows_cloud,
        "linux-container": __get_linux_container,
    }
elif sys.platform == "darwin":
    __DEV_ENVS: dict[str, Callable[[], type[DeveloperEnvironmentInterface[Any]]]] = {
        "linux-container": __get_linux_container,
        "windows-cloud": __get_windows_cloud,
    }
else:
    __DEV_ENVS: dict[str, Callable[[], type[DeveloperEnvironmentInterface[Any]]]] = {
        "linux-container": __get_linux_container,
        "windows-cloud": __get_windows_cloud,
    }

AVAILABLE_DEV_ENVS: list[str] = sorted(__DEV_ENVS)
