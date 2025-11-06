# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Any, Optional

from dda.config.constants import AppEnvVars
from dda.feature_flags.client import DatadogFeatureFlag
from dda.secrets.ssm import fetch_secret_ssm
from dda.secrets.vault import fetch_secret_ci
from dda.user.datadog import User
from dda.utils.platform import get_os_name

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.config.model import RootConfig


class FeatureFlagUser(User):
    def __init__(self, config: RootConfig) -> None:
        super().__init__(config)


class FeatureFlagManager(ABC):
    """
    A class for querying feature flags.
    """

    def __init__(self, app: Application) -> None:
        self._app = app
        # Manually implemented cache to avoid calling several time Feature flag backend on the same flag evaluation.
        # Cache key is a tuple of the flag, entity and scopes, to make it hashable.
        # For example after calling `enabled("test-flag", default=False, scopes={"user": "user1"}),
        # the cache will contain the result for the tuple ("test-flag", "entity", (("user", "user1"),)).
        self.__cache: dict[tuple[str, str, tuple[tuple[str, str], ...]], Any] = {}

    def enabled(self, flag: str, *, default: bool = False, scopes: Optional[dict[str, str]] = None) -> bool:
        entity = self.__entity
        base_scopes = self.__base_scopes
        if scopes is not None:
            base_scopes.update(scopes)

        attributes_items = base_scopes.items()
        tuple_attributes = tuple(((key, value) for key, value in sorted(attributes_items)))

        self._app.display_debug(
            f"Checking flag {flag} with targeting key {entity} and targeting attributes {tuple_attributes}"
        )
        flag_value = self.__check_flag(flag, entity, tuple_attributes)
        if flag_value is None:
            return default
        return flag_value

    def __check_flag(self, flag: str, entity: str, scopes: tuple[tuple[str, str], ...]) -> bool | None:
        if self.__client is None:
            self._app.display_debug("Feature flag client not initialized properly")
            return None

        cache_key = (flag, entity, scopes)
        if cache_key in self.__cache:
            return self.__cache[cache_key]

        flag_value = self.__client.get_flag_value(flag, entity, dict(scopes))
        self.__cache[cache_key] = flag_value
        return flag_value

    @abstractmethod
    def _get_client_token(self) -> str | None:
        pass

    @abstractmethod
    def _get_entity(self) -> str:
        pass

    @abstractmethod
    def _get_base_scopes(self) -> dict[str, str]:
        pass

    @cached_property
    def __client(self) -> DatadogFeatureFlag | None:
        token = self._get_client_token()
        if token is None:
            return None
        return DatadogFeatureFlag(token, self._app)

    @cached_property
    def __base_scopes(self) -> dict[str, str]:
        return self._get_base_scopes()

    @cached_property
    def __entity(self) -> str:
        return self._get_entity()


class CIFeatureFlagManager(FeatureFlagManager):
    """
    A class for querying feature flags in a CI environment.
    """

    def _get_client_token(self) -> str | None:
        self._app.display_debug(f"Getting client token for {sys.platform}")
        try:
            match sys.platform:
                case "win32":
                    return self.__get_client_token_windows()
                case "darwin":
                    return self.__get_client_token_macos()
                case "linux":
                    return self.__get_client_token_linux()
                case _:
                    return None
        except Exception as e:  # noqa: BLE001
            self._app.display_warning(f"Error getting client token: {e}, feature flag will be defaulted")
            return None

    def __get_client_token_windows(self) -> str | None:  # noqa: PLR6301
        if (client_token := os.getenv(AppEnvVars.FEATURE_FLAGS_CI_SSM_KEY_WINDOWS)) is None:
            return None
        return fetch_secret_ssm(name=client_token)

    def __get_client_token_macos(self) -> str | None:  # noqa: PLR6301
        if (client_token := os.getenv(AppEnvVars.FEATURE_FLAGS_CI_VAULT_KEY_MACOS)) is None:
            return None
        if (vault_path := os.getenv(AppEnvVars.FEATURE_FLAGS_CI_VAULT_PATH_MACOS)) is None:
            return None
        return fetch_secret_ci(vault_path, client_token)

    def __get_client_token_linux(self) -> str | None:  # noqa: PLR6301
        if (client_token := os.getenv(AppEnvVars.FEATURE_FLAGS_CI_VAULT_KEY)) is None:
            return None
        if (vault_path := os.getenv(AppEnvVars.FEATURE_FLAGS_CI_VAULT_PATH)) is None:
            return None
        return fetch_secret_ci(vault_path, client_token)

    def _get_entity(self) -> str:  # noqa: PLR6301
        return os.getenv("CI_JOB_ID", "default_entity")

    def _get_base_scopes(self) -> dict[str, str]:  # noqa: PLR6301
        return {
            "ci": "true",
            "ci.job.name": os.getenv("CI_JOB_NAME", ""),
            "ci.job.id": os.getenv("CI_JOB_ID", ""),
            "ci.stage.name": os.getenv("CI_JOB_STAGE", ""),
            "git.branch": os.getenv("CI_COMMIT_BRANCH", ""),
        }


class LocalFeatureFlagManager(FeatureFlagManager):
    """
    A class for querying feature flags. This is available as the
    [`Application.features`][dda.cli.application.Application.features] property.
    """

    def _get_client_token(self) -> str | None:  # noqa: PLR6301
        from contextlib import suppress

        from dda.secrets.api import fetch_client_token, read_client_token, save_client_token

        client_token: str | None = None
        with suppress(Exception):
            client_token = read_client_token()
            if not client_token:
                client_token = fetch_client_token()
                save_client_token(client_token)

        return client_token

    @property
    def __user(self) -> FeatureFlagUser:
        return FeatureFlagUser(self._app.config)

    def _get_entity(self) -> str:
        return self.__user.machine_id

    def _get_base_scopes(self) -> dict[str, str]:
        return {
            "platform": get_os_name(),
            "ci": "false",
            "user": self.__user.email,
        }
