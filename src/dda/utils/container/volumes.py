# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from dda.utils.container.model import Mount

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.utils.fs import Path


def exists(app: Application, name: str) -> bool:
    return app.tools.docker.volume_exists(name)


def remove(app: Application, name: str) -> None:
    app.tools.docker.volume_remove(name)


def list_with_prefix(app: Application, prefix: str) -> list[str]:
    return [v for v in app.tools.docker.volume_list() if v.startswith(prefix)]


def exec(  # noqa: A001
    app: Application,
    *,
    image: str,
    command: list[str],
    volumes: dict[str, str] | None = None,
    bind_mounts: dict[Path, str] | None = None,
    capture: bool = False,
    message: str | None = None,
) -> str | None:
    """Run a command in a throwaway helper container with the given mounts."""
    cmd: list[str] = ["run", "--rm"]
    if volumes:
        for vol_name, container_path in volumes.items():
            cmd += ["--mount", Mount(type="volume", source=vol_name, path=container_path).as_csv()]
    if bind_mounts:
        for host_path, container_path in bind_mounts.items():
            cmd += ["--mount", Mount(type="bind", source=str(host_path), path=container_path).as_csv()]
    cmd.append(image)
    cmd.extend(command)
    if message:
        app.display_waiting(message)
    if capture:
        return app.tools.docker.capture(cmd)
    app.tools.docker.wait(cmd)
    return None


_VOL_MOUNT = "/mnt/vol"


def copy_in(app: Application, *, image: str, volume: str, src: Path, dst: str) -> None:
    """Copy host path src into the volume at the volume-relative path dst."""
    target = f"{_VOL_MOUNT}/{dst.lstrip('/')}"
    exec(
        app,
        image=image,
        command=["sh", "-c", f"mkdir -p $(dirname {shlex.quote(target)}) && cp -a /mnt/src {shlex.quote(target)}"],
        volumes={volume: _VOL_MOUNT},
        bind_mounts={src: "/mnt/src"},
    )


def copy_out(app: Application, *, image: str, volume: str, src: str, dst: Path) -> None:
    """Copy the volume-relative path src to host path dst."""
    source = f"{_VOL_MOUNT}/{src.lstrip('/')}"
    exec(
        app,
        image=image,
        command=["sh", "-c", f"cp -a {shlex.quote(source)} /mnt/dst/"],
        volumes={volume: _VOL_MOUNT},
        bind_mounts={dst: "/mnt/dst"},
    )
