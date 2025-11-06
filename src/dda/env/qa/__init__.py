# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from dda.env.qa.interface import QAEnvironmentInterface
    from dda.env.qa.types.linux_container import LinuxContainer


DEFAULT_QA_ENV = "windows-container" if sys.platform == "win32" else "linux-container"


def get_qa_env(env_type: str) -> type[QAEnvironmentInterface]:
    getter = __QA_ENVS.get(env_type)
    if getter is None:
        message = f"Unknown QA environment: {env_type}"
        raise ValueError(message)

    return getter()


def __get_linux_container() -> type[LinuxContainer]:
    from dda.env.qa.types.linux_container import LinuxContainer

    return LinuxContainer


def __get_windows_container() -> type[QAEnvironmentInterface]:
    raise NotImplementedError


def __get_local_macos_vm() -> type[QAEnvironmentInterface]:
    raise NotImplementedError


if sys.platform == "win32":
    __QA_ENVS: dict[str, Callable[[], type[QAEnvironmentInterface[Any]]]] = {
        "windows-container": __get_windows_container,
        "linux-container": __get_linux_container,
    }
elif sys.platform == "darwin":
    __QA_ENVS: dict[str, Callable[[], type[QAEnvironmentInterface[Any]]]] = {
        "linux-container": __get_linux_container,
        "local-macos-vm": __get_local_macos_vm,
    }
else:
    __QA_ENVS: dict[str, Callable[[], type[QAEnvironmentInterface[Any]]]] = {
        "linux-container": __get_linux_container,
    }

AVAILABLE_QA_ENVS: list[str] = sorted(__QA_ENVS)
