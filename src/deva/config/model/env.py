# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field

from deva.env.dev import DEFAULT_DEV_ENV


class DevEnvConfig(Struct, frozen=True):
    default_type: str = field(name="default-type", default=DEFAULT_DEV_ENV)
    universal_shell: bool = field(name="universal-shell", default=False)


class EnvConfig(Struct, frozen=True):
    dev: DevEnvConfig = field(default_factory=DevEnvConfig)
