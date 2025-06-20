# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import pathlib
import sys
from contextlib import contextmanager
from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

    from _typeshed import FileDescriptorLike

disk_sync = os.fsync
# https://mjtsai.com/blog/2022/02/17/apple-ssd-benchmarks-and-f_fullsync/
# https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html
if sys.platform == "darwin":
    import fcntl

    if hasattr(fcntl, "F_FULLFSYNC"):

        def disk_sync(fd: FileDescriptorLike) -> None:
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


class Path(pathlib.Path):
    @cached_property
    def long_id(self) -> str:
        """
        Returns a SHA-256 hashed, URL-safe base64 encoded representation of the current path. This is useful
        on case-insensitive filesystems to identify paths that are the same.

        /// info | Caveat
        This identifier considers the filesystem to be case-insensitive on macOS. Although that is not a
        technical guarantee, it is in practice true.
        ///

        Returns:
            A unique identifier for the current path.
        """
        from base64 import urlsafe_b64encode
        from hashlib import sha256

        path = str(self)
        # Handle case-insensitive filesystems
        if sys.platform == "win32" or sys.platform == "darwin":
            path = path.casefold()

        digest = sha256(path.encode("utf-8")).digest()
        return urlsafe_b64encode(digest).decode("utf-8")

    @cached_property
    def id(self) -> str:
        """
        Returns:
            The first 8 characters of the [long ID][dda.utils.fs.Path.long_id].
        """
        return self.long_id[:8]

    def ensure_dir(self) -> None:
        """
        Ensure the current path is a directory. Equivalent to calling [`Path.mkdir`][pathlib.Path.mkdir]
        with `parents=True` and `exist_ok=True`.
        """
        self.mkdir(parents=True, exist_ok=True)

    def expand(self) -> Path:
        """
        Expand the current path by resolving the user home directory and environment variables.

        Returns:
            The new expanded path.
        """
        return Path(os.path.expanduser(os.path.expandvars(self)))

    def write_atomic(self, data: str | bytes, *args: Any, **kwargs: Any) -> None:
        """
        Atomically write data to the current path.

        Parameters:
            data: The data to write.

        Other parameters:
            *args: Additional arguments to pass to [`os.fdopen`][os.fdopen].
            **kwargs: Additional keyword arguments to pass to [`os.fdopen`][os.fdopen].
        """
        from tempfile import mkstemp

        fd, path = mkstemp(dir=self.parent)
        with os.fdopen(fd, *args, **kwargs) as f:
            f.write(data)
            f.flush()
            disk_sync(fd)

        os.replace(path, self)

    @contextmanager
    def as_cwd(self) -> Generator[Path, None, None]:
        """
        A context manager that changes the current working directory to the current path. Example:

        ```python
        with Path("foo").as_cwd():
            ...
        ```

        Yields:
            The current path.
        """
        origin = os.getcwd()
        os.chdir(self)

        try:
            yield self
        finally:
            os.chdir(origin)


@contextmanager
def temp_directory() -> Generator[Path, None, None]:
    """
    A context manager that creates a temporary directory and yields a path to it. Example:

    ```python
    with temp_directory() as temp_dir:
        ...
    ```

    Yields:
        The resolved path to the temporary directory, following all symlinks.
    """
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as d:
        yield Path(d).resolve()


@contextmanager
def change_workdir(new_workdir: Path) -> Generator[None, None, None]:
    """
    A context manager that temporarily selects the specified path as the working directory. Example:

    ```python
    with change_workdir("foo"):
        ...
    ```
    """
    new_workdir = Path(new_workdir).expand()
    old_workdir = Path.cwd().expand()
    os.chdir(new_workdir)

    try:
        yield
    finally:
        os.chdir(old_workdir)
