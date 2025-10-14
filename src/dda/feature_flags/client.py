# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import json
from typing import Any, Optional

from dda.utils.network.http.client import get_http_client


class DatadogFeatureFlag:
    """
    Direct HTTP client for Datadog Feature Flag API

    Based on the JavaScript implementation at:
    /Users/kevin.fairise/dd/openfeature-js-client/packages/browser/src/transport/fetchConfiguration.ts
    """

    def __init__(
        self,
        client_token: str,
    ):
        """
        Initialize the Datadog Feature Flag client

        Args:
            client_token: Your Datadog client token (starts with 'pub_')
            site: Datadog site (e.g., 'datadoghq.com', 'datadoghq.eu')
            env: Environment name
            application_id: Your application ID for RUM attribution
            service: Service name
            version: Application version
            flagging_proxy: Optional proxy URL for flagging configuration requests
            custom_headers: Optional custom headers to add to requests
        """
        self.client_token = client_token
        self.env = "Production"
        self.endpoint_url = f"https://preview.ff-cdn.datadoghq.com/precompute-assignments?dd_env={self.env}"
        self.application_id = "dda"
        self.__client = get_http_client()

    def _fetch_flags(
        self, targeting_key: str = "", targeting_attributes: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Fetch flag configuration from Datadog API

        Args:
            targeting_key: The targeting key (typically user ID)
            targeting_attributes: Additional targeting attributes (context)

        Returns:
            Dictionary containing the flag configuration response

        Raises:
            requests.HTTPError: If the API request fails
        """
        # Build headers
        headers = {
            "Content-Type": "application/vnd.api+json",
            "dd-client-token": self.client_token,
        }

        if self.application_id:
            headers["dd-application-id"] = self.application_id

        # Stringify all targeting attributes
        stringified_attributes = {}
        if targeting_attributes:
            for key, value in targeting_attributes.items():
                if isinstance(value, str):
                    stringified_attributes[key] = value
                else:
                    stringified_attributes[key] = json.dumps(value)

        # Build request payload (following JSON:API format)
        payload = {
            "data": {
                "type": "precompute-assignments-request",
                "attributes": {
                    "env": {
                        "dd_env": self.env,
                    },
                    "sdk": {
                        "name": "python-example",
                        "version": "0.1.0",
                    },
                    "subject": {
                        "targeting_key": targeting_key,
                        "targeting_attributes": stringified_attributes,
                    },
                },
            },
        }

        try:
            # Make the request
            response = self.__client.post(self.endpoint_url, headers=headers, json=payload, timeout=10)
        except Exception:  # noqa: BLE001
            return {}

        return response.json()

    def get_flag_value(self, flag_key: str, context: dict[str, Any]) -> Any:
        """
        Get a flag value by key

        Args:
            flag_key: The flag key to evaluate
            default_value: Default value if flag is not found
            targeting_key: The targeting key (typically user ID)
            targeting_attributes: Additional targeting attributes

        Returns:
            The flag value or default value
        """
        try:
            response = self._fetch_flags(context["targeting_key"], context["targeting_attributes"])
            # Navigate the response structure
            flags = response.get("data", {}).get("attributes", {}).get("flags", {})
            if flag_key in flags:
                return flags[flag_key].get("variationValue", None)

        except Exception:  # noqa: BLE001
            return None

        return None
