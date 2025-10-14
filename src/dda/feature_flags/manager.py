# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, Optional

from dda.feature_flags.client import DatadogFeatureFlag
from dda.utils.ci import running_in_ci
from dda.utils.user import User

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.config.model import RootConfig


class FeatureFlagUser(User):
    def __init__(self, config: RootConfig) -> None:
        super().__init__(config)


class FeatureFlagManager:
    """
    A class for querying feature flags. This is available as the
    [`Application.ff`][dda.cli.application.Application.ff] property.
    """

    def __init__(self, app: Application) -> None:
        self.__app = app

        self.__started = False

        if self.client_token is not None:
            self.__ff_client = DatadogFeatureFlag(self.client_token)
            self.__started = True

        self.__cache: dict[tuple[str, str, tuple[tuple[str, str], ...]], Any] = {}

    @cached_property
    def client_token(self) -> str | None:
        from contextlib import suppress

        from dda.utils.secrets.secrets import fetch_client_token, read_client_token, save_client_token

        client_token: str | None = None
        with suppress(Exception):
            client_token = read_client_token()
            if not client_token:
                client_token = fetch_client_token()
                save_client_token(client_token)

        return client_token

    @property
    def user(self) -> FeatureFlagUser:
        return FeatureFlagUser(self.__app.config)

    def get_targeting_key(self) -> str:
        if running_in_ci():
            import os

            return os.getenv("CI_JOB_ID", "default_job_id")

        return self.user.machine_id

    def check_flag(self, flag_key: str, default_value: Any, extra_attributes: Optional[dict[str, str]] = None) -> bool:
        if not self.__started:
            return default_value

        targeting_key = self.get_targeting_key()
        targeting_attributes = self._get_base_context()
        if extra_attributes is not None:
            targeting_attributes.update(extra_attributes)

        attributes_items = targeting_attributes.items()
        tuple_attributes = tuple(((key, value) for key, value in sorted(attributes_items)))

        self.__app.display_debug(
            f"Checking flag {flag_key} with targeting key {targeting_key} and targeting attributes {tuple_attributes}"
        )
        flag_value = self._check_flag(flag_key, targeting_key, tuple_attributes)
        if flag_value is None:
            return default_value
        return flag_value

    def _check_flag(self, flag_key: str, targeting_key: str, targeting_attributes: tuple[tuple[str, str], ...]) -> bool:
        cache_key = (flag_key, targeting_key, targeting_attributes)
        if cache_key in self.__cache:
            return self.__cache[cache_key]

        context = {
            "targeting_key": targeting_key,
            "targeting_attributes": dict(targeting_attributes),
        }

        flag_value = self.__ff_client.get_flag_value(flag_key, context)
        self.__cache[cache_key] = flag_value
        return flag_value

    def _get_base_context(self) -> dict[str, str]:
        return {
            "platform": "toto",
            "ci": "true" if running_in_ci() else "false",
            "env": "prod",
            "user": self.user.email,
        }
