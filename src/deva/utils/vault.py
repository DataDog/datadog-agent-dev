# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import urllib.parse
import webbrowser

import hvac

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


def init_client():
    client = hvac.Client(url="https://vault.us1.ddbuild.io")

    auth_url_response = client.auth.oidc.oidc_authorization_url_request(redirect_uri=OIDC_REDIRECT_URI, role=None)
    auth_url = auth_url_response["data"]["auth_url"]
    if not auth_url:
        return None

    params = urllib.parse.parse_qs(auth_url.split("?")[1])
    auth_url_nonce = params["nonce"][0]
    auth_url_state = params["state"][0]

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
def login_oidc_get_token():
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class HttpServ(HTTPServer):
        def __init__(self, *args, **kwargs):
            HTTPServer.__init__(self, *args, **kwargs)
            self.token = None

    class AuthHandler(BaseHTTPRequestHandler):
        token = ""

        def do_GET(self):  # noqa: N802
            params = urllib.parse.parse_qs(self.path.split("?")[1])
            self.server.token = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(str.encode(SELF_CLOSING_PAGE))

    server_address = ("", OIDC_CALLBACK_PORT)
    httpd = HttpServ(server_address, AuthHandler)
    httpd.handle_request()
    return httpd.token


def fetch_secret(name: str, key: str):
    client = init_client()
    if client is None:
        return None
    secret = client.secrets.kv.v2.read_secret_version(path=name, mount_point="kv")
    return secret["data"]["data"][key]
