# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
import webbrowser
from typing import Any

import hvac
from ada_url import URL, URLSearchParams

from dda.utils.ci import running_in_ci

VAULT_URL = "https://vault.us1.ddbuild.io"
OIDC_CALLBACK_PORT = 8250
OIDC_REDIRECT_URI = f"http://localhost:{OIDC_CALLBACK_PORT}/oidc/callback"
SELF_CLOSING_PAGE = """
<!doctype html>
<html>
<head>
<script>
// Closes IE, Edge, Chrome, Brave
window.onload = function load() {
  window.open('', '_self', '');
  window.close();
};
</script>
</head>
<body>
  <p>Authentication successful, you can close the browser now.</p>
  <script>
    // Needed for Firefox security
    setTimeout(function() {
          window.close()
    }, 5000);
  </script>
</body>
</html>
"""


def init_client() -> hvac.Client:
    logging.info("Initializing HVAC client")
    client = hvac.Client(url=VAULT_URL)

    auth_url_response = client.auth.oidc.oidc_authorization_url_request(redirect_uri=OIDC_REDIRECT_URI, role=None)
    logging.info("Received auth URL response: %s", auth_url_response)
    auth_url = auth_url_response["data"]["auth_url"]
    if not auth_url:
        message = "No auth URL in response"
        raise ValueError(message)

    params = URLSearchParams(URL(auth_url).search)
    auth_url_nonce = params.get("nonce")
    auth_url_state = params.get("state")

    webbrowser.open(auth_url)
    token = login_oidc_get_token()

    auth_result = client.auth.oidc.oidc_callback(
        code=token,
        path="oidc",
        nonce=auth_url_nonce,
        state=auth_url_state,
    )
    new_token = auth_result["auth"]["client_token"]

    # If you want to continue using the client here
    # update the client to use the new token
    client.token = new_token
    return client


# handles the callback
def login_oidc_get_token() -> str:
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Server(HTTPServer):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.token = ""

    class AuthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            params = URLSearchParams(self.path)
            self.server.token = params.get("code")  # type: ignore[attr-defined]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(SELF_CLOSING_PAGE.encode())

    server_address = ("", OIDC_CALLBACK_PORT)
    httpd = Server(server_address, AuthHandler)
    httpd.handle_request()
    return httpd.token


def fetch_secret(name: str, key: str) -> str:
    if running_in_ci():
        return fetch_secret_ci(name, key)
    return fetch_secret_local(name, key)


def fetch_secret_local(name: str, key: str) -> str:
    client = init_client()
    secret = client.secrets.kv.v2.read_secret_version(path=name, mount_point="kv")
    return secret["data"]["data"][key]


def fetch_secret_ci(name: str, key: str) -> str:
    client = hvac.Client()
    secret = client.secrets.kv.v2.read_secret_version(path=name, mount_point="kv")
    return secret["data"]["data"][key]
