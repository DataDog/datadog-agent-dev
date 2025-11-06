# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, Optional

from dda.feature_flags.client import DatadogFeatureFlag
from dda.user.datadog import User
from dda.utils.ci import running_in_ci

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.config.model import RootConfig


class FeatureFlagUser(User):
    def __init__(self, config: RootConfig) -> None:
        super().__init__(config)


class FeatureFlagManager:
    """
    A class for querying feature flags. This is available as the
    [`Application.features`][dda.cli.application.Application.features] property.
    """

    def __init__(self, app: Application) -> None:
        self.__app = app
        # Manually implemented cache to avoid calling several time Feature flag backend on the same flag evaluation.
        # Cache key is a tuple of the flag, entity and scopes, to make it hashable.
        # For example after calling `enabled("test-flag", default=False, scopes={"user": "user1"}),
        # the cache will contain the result for the tuple ("test-flag", "entity", (("user", "user1"),)).
        self.__cache: dict[tuple[str, str, tuple[tuple[str, str], ...]], Any] = {}

    @cached_property
    def __client(self) -> DatadogFeatureFlag | None:
        if running_in_ci():  # We do not support feature flags token retrieval in the CI yet.
            return None

        from contextlib import suppress

        from dda.secrets.api import fetch_client_token, read_client_token, save_client_token

        client_token: str | None = None
        with suppress(Exception):
            client_token = read_client_token()
            if not client_token:
                client_token = fetch_client_token()
                save_client_token(client_token)

        return DatadogFeatureFlag(client_token, self.__app)

    @property
    def __user(self) -> FeatureFlagUser:
        return FeatureFlagUser(self.__app.config)

    def __get_entity(self) -> str:
        if running_in_ci():
            import os

            return os.getenv("CI_JOB_ID", "default_job_id")

        return self.__user.machine_id

    def enabled(self, flag: str, *, default: bool = False, scopes: Optional[dict[str, str]] = None) -> bool:
        entity = self.__get_entity()
        base_scopes = self.__get_base_scopes()
        if scopes is not None:
            base_scopes.update(scopes)

        attributes_items = base_scopes.items()
        tuple_attributes = tuple(((key, value) for key, value in sorted(attributes_items)))

        self.__app.display_debug(f"Checking flag {flag} with entity {entity} and scopes {base_scopes}")
        flag_value = self.__check_flag(flag, entity, tuple_attributes)
        if flag_value is None:
            return default
        return flag_value

    def __check_flag(self, flag: str, entity: str, scopes: tuple[tuple[str, str], ...]) -> bool | None:
        if self.__client is None:
            self.__app.display_debug("Feature flag client not initialized properly")
            return None

        cache_key = (flag, entity, scopes)
        if cache_key in self.__cache:
            return self.__cache[cache_key]

        flag_value = self.__client.get_flag_value(flag, entity, dict(scopes))
        self.__cache[cache_key] = flag_value
        return flag_value

    def __get_base_scopes(self) -> dict[str, str]:
        return {
            "ci": "true" if running_in_ci() else "false",
            "user": self.__user.email,
        }
