# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dda._version import __version__

if TYPE_CHECKING:
    from dda.cli.application import Application


class DatadogFeatureFlag:
    """
    Direct HTTP client for Datadog Feature Flag API
    """

    def __init__(self, client_token: str | None, app: Application):
        """
        Initialize the Datadog Feature Flag client

        Parameters:
            client_token: Your Datadog client token (starts with 'pub_')
            app: The application instance
        """
        self.__client_token = client_token
        self.__env = "Production"
        self.__url = f"https://preview.ff-cdn.datadoghq.com/precompute-assignments?dd_env={self.__env}"
        self.__app_id = "dda"
        self.__app = app

    def _fetch_flags(
        self, targeting_key: str = "", targeting_attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Fetch flag configuration from Datadog API

        Parameters:
            targeting_key: The targeting key (typically user ID)
            targeting_attributes: Additional targeting attributes (context)

        Returns:
            Dictionary containing the flag configuration response

        Raises:
            httpx.HTTPError: If the request fails
            RuntimeError: If an unexpected error occurs
        """
        if not self.__client_token:
            return {}

        from httpx import HTTPError

        # Build headers
        headers = {
            "Content-Type": "application/vnd.api+json",
            "dd-client-token": self.__client_token,
            "dd-application-id": self.__app_id,
        }

        # Build request payload (following JSON:API format)
        payload = {
            "data": {
                "type": "precompute-assignments-request",
                "attributes": {
                    "env": {
                        "dd_env": self.__env,
                    },
                    "sdk": {
                        "name": "dda",
                        "version": __version__,
                    },
                    "subject": {
                        "targeting_key": targeting_key,
                        "targeting_attributes": targeting_attributes,
                    },
                },
            },
        }

        try:
            # Make the request
            response = self.__app.http.client().post(self.__url, headers=headers, json=payload)
        except HTTPError as e:
            self.__app.display_warning(f"Error fetching flags: {e}")
        except Exception as e:
            err_message = f"Error fetching flags: {e}"
            raise RuntimeError(err_message) from e

        return response.json()

    def get_flag_value(self, flag: str, targeting_key: str, targeting_attributes: dict[str, Any]) -> bool | None:
        """
        Get a flag value by key

        Parameters:
            flag: The flag key to evaluate
            targeting_key: The targeting key to use for feature flag evaluation
            targeting_attributes: The targeting attributes to use for feature flag evaluation

        Returns:
            The flag value or None if the flag is not found

        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If the flag is not found
            RuntimeError: If an unexpected error occurs
        """
        response = self._fetch_flags(targeting_key, targeting_attributes)
        flags = response.get("data", {}).get("attributes", {}).get("flags", {})
        if flag in flags:
            return flags[flag].get("variationValue", None)
        err_message = f"Flag {flag} not found"
        raise ValueError(err_message) from None
