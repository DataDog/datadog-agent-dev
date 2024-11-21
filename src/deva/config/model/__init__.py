# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any

from msgspec import Struct, convert, field, to_builtins

from deva.config.model.env import EnvConfig
from deva.config.model.git import GitConfig
from deva.config.model.github import GitHubConfig
from deva.config.model.orgs import OrgConfig
from deva.config.model.storage import StorageDirs
from deva.config.model.telemetry import TelemetryConfig
from deva.config.model.terminal import TerminalConfig
from deva.utils.fs import Path


def _default_orgs() -> dict[str, OrgConfig]:
    return {"default": OrgConfig()}


class RootConfig(Struct, frozen=True, omit_defaults=True):
    orgs: dict[str, OrgConfig] = field(default_factory=_default_orgs)
    env: EnvConfig = field(default_factory=EnvConfig)
    envs: dict[str, dict[str, Any]] = {}
    storage: StorageDirs = field(default_factory=StorageDirs)
    git: GitConfig = field(default_factory=GitConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    terminal: TerminalConfig = field(default_factory=TerminalConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)


def construct_model(data: dict[str, Any]) -> RootConfig:
    return convert(data, RootConfig, dec_hook=__dec_hook)


def get_default_toml_data() -> dict[str, Any]:
    import datetime

    return to_builtins(
        RootConfig(),
        str_keys=True,
        builtin_types=(datetime.datetime, datetime.date, datetime.time),
        enc_hook=__enc_hook,
    )


def __dec_hook(type: type[Any], obj: Any) -> Any:  # noqa: A002
    if type is Path:
        return Path(obj)

    message = f"Cannot decode: {obj!r}"
    raise ValueError(message)


def __enc_hook(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)

    message = f"Cannot encode: {obj!r}"
    raise NotImplementedError(message)
