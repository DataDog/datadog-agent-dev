# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from typing import Literal

from msgspec import Struct

from dda.utils.fs import Path


class Mount(Struct):
    """
    This represents [mount configuration](https://docs.docker.com/engine/storage/volumes/#options-for---mount)
    for a container.
    """

    type: Literal["bind", "volume"]
    """
    The type of mount, either [`bind`](https://docs.docker.com/engine/storage/bind-mounts/) or
    [`volume`](https://docs.docker.com/engine/storage/volumes/).
    """
    path: str
    """
    The path where the file or directory is mounted in the container.
    """
    source: str | None = None
    """
    For bind mounts, this is the path to the file or directory on the host. For volume mounts, this is
    the name of the volume. Anonymous volumes must not set this.
    """
    read_only: bool = False
    """
    Whether the mount is read-only.
    """
    volume_options: dict[str, str] = {}
    """
    Additional options for the `volume` mounts.
    """

    def __post_init__(self) -> None:
        if self.type == "bind":
            if self.source is None:
                msg = "source is required for bind mounts"
                raise ValueError(msg)

            # https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/topics/#path-conversion-errors-on-windows
            if sys.platform == "win32":
                path = Path(self.source)
                if path.is_absolute():
                    drive_letter = path.drive.replace(":", "").lower()
                    self.source = f"/{path.as_posix().replace(path.drive, drive_letter, 1)}"

    def as_csv(self) -> str:
        """
        This returns a CSV representation of the mount configuration. This can be used directly by the
        `--mount` flag of the `docker run` command.
        """
        import csv
        from io import StringIO

        with StringIO() as s:
            columns = [f"type={self.type}"]
            if self.source is not None:
                columns.append(f"src={self.source}")

            columns.append(f"dst={self.path}")
            if self.read_only:
                columns.append("ro")
            if self.volume_options:
                for option, value in self.volume_options.items():
                    columns.append(f"volume-opt={option}={value}")

            writer = csv.writer(s)
            writer.writerow(columns)
            return s.getvalue().rstrip()
