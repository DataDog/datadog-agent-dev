# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
"""Browser proxy daemon.

Serves a minimal HTTP endpoint that opens URLs in the host's default browser.
Designed to be started as a detached subprocess by ``LinuxContainer``.

* Binds to ``0.0.0.0`` so Docker containers can reach it via
  ``host.docker.internal``.
* Accepts ``GET /open?url=<url>`` and opens only ``http``/``https`` URLs.
* When the URL contains a ``redirect_uri`` pointing at ``localhost:{port}``,
  an SSH local-port-forward is established *before* the browser opens so that
  the auth callback from the browser reaches the container service.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

# Maximum depth when recursing into nested redirect parameters.
_MAX_REDIRECT_DEPTH = 5

# How long to keep an SSH tunnel alive after it is established (seconds).
_TUNNEL_LIFETIME = 600

# How long to wait for SSH to bind the callback port (seconds).
_TUNNEL_BIND_TIMEOUT = 5.0

_ssh_port: int | None = None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/open":
            params = urllib.parse.parse_qs(parsed.query)
            urls = params.get("url", [])
            if urls:
                url = urls[0]
                if url.startswith(("http://", "https://")):
                    _handle_open(url)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


# ---------------------------------------------------------------------------
# Core open logic
# ---------------------------------------------------------------------------


def _handle_open(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    redirect = _find_redirect_url(urllib.parse.parse_qs(parsed.query))

    if redirect is not None and _is_localhost(redirect.hostname or ""):
        port = redirect.port or (443 if redirect.scheme == "https" else 80)
        if _ssh_port is not None:
            _setup_port_forward(_ssh_port, port)

    _open_browser(url)


def _find_redirect_url(
    params: dict[str, list[str]],
    depth: int = 0,
) -> urllib.parse.ParseResult | None:
    """Return the first localhost redirect URL found in *params*, or None."""
    if depth > _MAX_REDIRECT_DEPTH:
        return None
    for key in ("redirect_uri", "redirect_url", "redirect"):
        value = (params.get(key) or [None])[0]
        if value:
            try:
                return urllib.parse.urlparse(value)
            except Exception:  # noqa: BLE001
                pass
    # Recurse into nested URL-valued query parameters.
    for values in params.values():
        for v in values:
            try:
                nested = urllib.parse.urlparse(v)
                if nested.query:
                    found = _find_redirect_url(urllib.parse.parse_qs(nested.query), depth + 1)
                    if found is not None:
                        return found
            except Exception:  # noqa: BLE001
                pass
    return None


def _is_localhost(host: str) -> bool:
    return host in ("localhost", "127.0.0.1", "::1", "0.0.0.0")


# ---------------------------------------------------------------------------
# SSH port-forward helpers
# ---------------------------------------------------------------------------


def _setup_port_forward(ssh_port: int, callback_port: int) -> None:
    """Bind ``127.0.0.1:{callback_port}`` on the host and forward it to the
    container's ``localhost:{callback_port}`` via SSH local port forwarding.

    Blocks until the port is bound (or the attempt times out / fails) so the
    caller can safely open the browser immediately after returning.
    """
    proc = subprocess.Popen(
        [
            "ssh",
            "-N",
            "-q",
            "-p",
            str(ssh_port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-L",
            f"127.0.0.1:{callback_port}:localhost:{callback_port}",
            "dd@localhost",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if not _wait_for_port_bound(proc, callback_port):
        proc.terminate()
        return

    def _cleanup() -> None:
        time.sleep(_TUNNEL_LIFETIME)
        try:
            proc.terminate()
        except Exception:  # noqa: BLE001
            pass

    threading.Thread(target=_cleanup, daemon=True).start()


def _wait_for_port_bound(proc: subprocess.Popen, port: int) -> bool:
    """Return True once ssh has bound *port* on 127.0.0.1, False on timeout or
    early ssh exit.

    Detection strategy: try to bind the port ourselves — if that raises
    EADDRINUSE it means ssh already owns it.
    """
    deadline = time.monotonic() + _TUNNEL_BIND_TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False  # ssh exited early (e.g. ExitOnForwardFailure)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
            # Still bindable — ssh not ready yet
            time.sleep(0.05)
        except OSError:
            return True  # EADDRINUSE: ssh has claimed the port
    return False


# ---------------------------------------------------------------------------
# Browser open
# ---------------------------------------------------------------------------


def _open_browser(url: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", url], check=False)  # noqa: S603, S607
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", url], check=False)  # noqa: S603, S607
    else:
        import webbrowser

        webbrowser.open(url)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def serve(port: int, ssh_port: int | None = None) -> None:
    global _ssh_port  # noqa: PLW0603
    _ssh_port = ssh_port
    HTTPServer(("0.0.0.0", port), _Handler).serve_forever()  # noqa: S104


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int)
    parser.add_argument("--ssh-port", type=int, default=None)
    args = parser.parse_args()
    serve(args.port, args.ssh_port)
