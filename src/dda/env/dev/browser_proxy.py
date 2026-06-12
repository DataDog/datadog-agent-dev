# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
"""Browser proxy daemon — shared across all dev containers.

Serves a minimal HTTP endpoint that opens URLs in the host's default browser.
Started once on the host; all containers share the same instance.

* Binds to ``0.0.0.0`` so Docker containers can reach it via
  ``host.docker.internal``.
* Accepts ``GET /open?url=<url>&ssh_port=<port>`` and opens only
  ``http``/``https`` URLs.
* When the URL contains a ``redirect_uri`` pointing at ``localhost:{port}``,
  an SSH local-port-forward is established *before* the browser opens so that
  the auth callback from the browser reaches the container service.
* ``ssh_port`` is supplied per-request (embedded in each container's
  xdg-open script) so the single daemon can serve multiple containers.
"""

from __future__ import annotations

import contextlib
import logging
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

log = logging.getLogger(__name__)

# Maximum depth when recursing into nested redirect parameters.
_MAX_REDIRECT_DEPTH = 5

# How long to keep an SSH tunnel alive after it is established (seconds).
_TUNNEL_LIFETIME = 300

# How long to wait for SSH to bind the callback port (seconds).
_TUNNEL_BIND_TIMEOUT = 5.0

# Maps (ssh_port, callback_port) → live SSH Popen for that tunnel.
# Keyed by both ports so tunnels from different containers to the same
# callback port are tracked independently.
_active_tunnels: dict[tuple[int, int], subprocess.Popen] = {}
_tunnel_lock = threading.Lock()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/open":
            params = urllib.parse.parse_qs(parsed.query)
            urls = params.get("url", [])
            if urls:
                url = urls[0]
                if url.startswith(("http://", "https://")):
                    ssh_ports = params.get("ssh_port", [])
                    try:
                        ssh_port: int | None = int(ssh_ports[0]) if ssh_ports else None
                    except ValueError:
                        ssh_port = None
                    log.info("open request: url=%s ssh_port=%s", url, ssh_port)
                    _handle_open(url, ssh_port)
                else:
                    log.warning("rejected non-http(s) url: %s", url)
            else:
                log.warning("open request missing url parameter")
        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: PLR6301
        log.debug(fmt, *args)


# ---------------------------------------------------------------------------
# Core open logic
# ---------------------------------------------------------------------------


def _handle_open(url: str, ssh_port: int | None) -> None:
    parsed = urllib.parse.urlparse(url)
    redirect = _find_redirect_url(urllib.parse.parse_qs(parsed.query))

    if redirect is not None and _is_localhost(redirect.hostname or ""):
        port = redirect.port or (443 if redirect.scheme == "https" else 80)
        log.info("detected OAuth callback redirect to localhost:%d", port)
        if ssh_port is not None:
            _setup_port_forward(ssh_port, port)
        else:
            log.warning("no ssh_port provided — skipping port forward for callback port %d", port)

    _open_browser(url)


def _find_redirect_url(
    params: dict[str, list[str]],
    depth: int = 0,
) -> urllib.parse.ParseResult | None:
    """Return the first localhost redirect URL found in *params*, or None."""
    if depth > _MAX_REDIRECT_DEPTH:
        return None
    for key in ("redirect_uri", "redirect_url", "redirect"):
        values = params.get(key)
        value = values[0] if values else None
        if value:
            with contextlib.suppress(Exception):
                return urllib.parse.urlparse(value)
    # Recurse into nested URL-valued query parameters.
    for values in params.values():
        for v in values:
            with contextlib.suppress(Exception):
                nested = urllib.parse.urlparse(v)
                if nested.query:
                    found = _find_redirect_url(urllib.parse.parse_qs(nested.query), depth + 1)
                    if found is not None:
                        return found
    return None


def _is_localhost(host: str) -> bool:
    return host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}  # noqa: S104


# ---------------------------------------------------------------------------
# SSH port-forward helpers
# ---------------------------------------------------------------------------

# Cmdline markers that identify an SSH tunnel spawned by this daemon.
_TUNNEL_MARKERS = ("dd@localhost", "-L")


def _is_our_tunnel(cmdline: list[str], ssh_port: int, callback_port: int) -> bool:
    """Return True if *cmdline* belongs to a tunnel we would have spawned."""
    joined = " ".join(cmdline)
    return (
        "dd@localhost" in joined
        and f"-p\x00{ssh_port}" in "\x00".join(cmdline)
        and f"127.0.0.1:{callback_port}:localhost:{callback_port}" in joined
    )


def _kill_tunnel_process(proc: subprocess.Popen | None) -> None:
    """Terminate *proc*, escalating to SIGKILL if it does not exit within 1 s."""
    if proc is None:
        return
    with contextlib.suppress(Exception):
        proc.terminate()
    for _ in range(20):
        if proc.poll() is not None:
            return
        time.sleep(0.05)
    with contextlib.suppress(Exception):
        proc.kill()


def _kill_orphaned_tunnels(ssh_port: int | None = None, callback_port: int | None = None) -> None:
    """Kill SSH tunnel processes left over from a previous daemon instance.

    When called at startup (both args None) it sweeps all processes that match
    our tunnel markers.  When called before setting up a specific tunnel it
    targets only processes matching that exact ``(ssh_port, callback_port)`` pair.
    """
    try:
        import psutil
    except ImportError:
        return

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = proc.info["name"] or ""
            cmdline: list[str] = proc.info["cmdline"] or []
            if "ssh" not in name.lower() and not any("ssh" in c for c in cmdline[:2]):
                continue
            joined = " ".join(cmdline)
            if not all(m in joined for m in _TUNNEL_MARKERS):
                continue
            if (
                ssh_port is not None
                and callback_port is not None
                and not _is_our_tunnel(cmdline, ssh_port, callback_port)
            ):
                continue
            log.info("killing orphaned tunnel pid=%d cmdline=%s", proc.pid, joined)
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def _setup_port_forward(ssh_port: int, callback_port: int) -> None:
    """Bind ``127.0.0.1:{callback_port}`` on the host and forward it to the
    container's ``localhost:{callback_port}`` via SSH local port forwarding.

    Serialised per ``(ssh_port, callback_port)`` pair.  Any orphaned SSH tunnel
    process for that pair is killed before a new one is started so that a daemon
    restart never leaves a stale tunnel blocking the port.
    """
    tunnel_key = (ssh_port, callback_port)
    with _tunnel_lock:
        existing = _active_tunnels.get(tunnel_key)
        if existing is not None and existing.poll() is None:
            log.info("reusing existing tunnel ssh_port=%d -> callback_port=%d", ssh_port, callback_port)
            return

        # Kill any orphaned SSH process holding this port from a previous daemon.
        _kill_orphaned_tunnels(ssh_port, callback_port)

        log.info("establishing SSH tunnel ssh_port=%d -> callback_port=%d", ssh_port, callback_port)
        ssh = shutil.which("ssh") or "ssh"
        proc = subprocess.Popen(
            [
                ssh,
                "-N",
                "-q",
                "-F",
                "/dev/null",
                "-o",
                "ExitOnForwardFailure=yes",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-p",
                str(ssh_port),
                "-L",
                f"127.0.0.1:{callback_port}:localhost:{callback_port}",
                "dd@localhost",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        if not _wait_for_port_bound(proc, callback_port):
            stderr_output = proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
            log.warning(
                "failed to bind callback_port=%d (ssh_port=%d)%s",
                callback_port,
                ssh_port,
                f": {stderr_output}" if stderr_output else "",
            )
            _kill_tunnel_process(proc)
            return

        log.info("tunnel established ssh_port=%d -> callback_port=%d", ssh_port, callback_port)
        _active_tunnels[tunnel_key] = proc

    def _cleanup() -> None:
        time.sleep(_TUNNEL_LIFETIME)
        with _tunnel_lock:
            _kill_tunnel_process(proc)
            _active_tunnels.pop(tunnel_key, None)
        log.info("tunnel expired ssh_port=%d -> callback_port=%d", ssh_port, callback_port)

    threading.Thread(target=_cleanup, daemon=True).start()


def _wait_for_port_bound(proc: subprocess.Popen, port: int) -> bool:
    """Return True once *our* ssh process has bound *port* on 127.0.0.1.

    Detection strategy: try to bind the port ourselves — if that raises
    EADDRINUSE we know *something* holds it.  We then confirm it is our SSH
    process and not a pre-existing listener by waiting up to 500 ms for SSH to
    exit.  With ``ExitOnForwardFailure=yes``, SSH exits within ~100-300 ms of
    starting if it could not bind the port (either pre-occupied or auth failure).
    If SSH is still alive after that window, it is the port owner.
    """
    deadline = time.monotonic() + _TUNNEL_BIND_TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False  # ssh exited — auth failure or pre-occupied port
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
            # Still bindable — ssh not ready yet
            time.sleep(0.05)
        except OSError:
            # Port is taken by something.  SSH may have just started and not
            # yet had time to fail.  Poll for up to 500 ms: if SSH exits it
            # did not own the port; if it stays alive it bound the port itself.
            for _ in range(10):
                if proc.poll() is not None:
                    return False
                time.sleep(0.05)
            return proc.poll() is None
    return False


# ---------------------------------------------------------------------------
# Browser open
# ---------------------------------------------------------------------------


def _open_browser(url: str) -> None:
    import webbrowser

    log.info("opening browser: %s", url)
    webbrowser.open(url)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def serve(port: int, log_file: str | None = None) -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file) if log_file else logging.StreamHandler(),
        ],
    )
    log.info("browser proxy starting on port %d", port)
    _kill_orphaned_tunnels()
    HTTPServer(("0.0.0.0", port), _Handler).serve_forever()  # noqa: S104


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int)
    parser.add_argument("--log-file", default=None)
    args = parser.parse_args()
    serve(args.port, log_file=args.log_file)
