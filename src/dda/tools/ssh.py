# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from base64 import b64decode, b64encode
from contextlib import contextmanager
from functools import cached_property
from hashlib import sha256
from typing import TYPE_CHECKING

import msgspec

from dda.tools.base import ExecutionContext, Tool
from dda.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Generator


MANAGED_CONFIG_DIR = ".dda"
MINIMUM_PUBLIC_KEY_FIELDS = 2


class PublicKey(msgspec.Struct, frozen=True):
    """A normalized SSH public key with its OpenSSH SHA-256 fingerprint."""

    algorithm: str
    data: str

    @classmethod
    def parse(cls, value: str) -> PublicKey | None:
        fields = value.strip().removeprefix("key::").split()
        if len(fields) < MINIMUM_PUBLIC_KEY_FIELDS or not fields[0].startswith(("ssh-", "ecdsa-", "sk-")):
            return None
        try:
            b64decode(fields[1], validate=True)
        except ValueError:
            return None

        return cls(algorithm=fields[0], data=fields[1])

    @property
    def line(self) -> str:
        return f"{self.algorithm} {self.data}"

    @property
    def fingerprint(self) -> str:
        key_data = b64decode(self.data, validate=True)
        digest = b64encode(sha256(key_data).digest()).decode("ascii").rstrip("=")
        return f"SHA256:{digest}"


class PublicKeyFile(msgspec.Struct, frozen=True):
    """A selector containing a parsed key, an error message, or `None` when missing."""

    path: str
    result: PublicKey | str | None

    def resolve(self, agent_keys: dict[str, PublicKey], *, required: bool = False) -> PublicKey | str:
        """Return the selected agent key or explain why it is unavailable."""

        if self.result is None:
            qualifier = "Required public-key selector" if required else "Public-key selector"
            return f"{qualifier} `{self.path}` is missing."
        if isinstance(self.result, str):
            return self.result
        if self.result.fingerprint not in agent_keys:
            return (
                f"Public-key selector `{self.path}` selects {self.result.fingerprint}, but that key is not "
                "loaded in the host SSH agent."
            )
        return self.result


class SSH(Tool):
    """
    Example usage:

    ```python
    command = app.tools.ssh.get_command(
        "user@example.com", remote_command="uname -a"
    )
    app.subprocess.run(command)
    ```
    """

    @contextmanager
    def execution_context(self, command: list[str]) -> Generator[ExecutionContext, None, None]:
        yield ExecutionContext(command=[self.path, *command], env_vars={})

    @cached_property
    def path(self) -> str:
        import shutil

        return shutil.which("ssh") or "ssh"

    @cached_property
    def agent_path(self) -> str:
        import shutil

        return shutil.which("ssh-add") or "ssh-add"

    @property
    def config_dir(self) -> Path:
        """The user's SSH configuration directory."""

        return Path.home() / ".ssh"

    def get_command(
        self,
        destination: str,
        *,
        port: int | str | None = None,
        forward_agent: bool | None = None,
        quiet: bool = False,
        allocate_tty: bool = False,
        remote_command: str | None = None,
    ) -> list[str]:
        """Build a complete SSH connection command without executing it."""

        command = [self.path]
        if forward_agent is not None:
            command.append("-A" if forward_agent else "-a")
        if quiet:
            command.append("-q")
        if allocate_tty:
            command.append("-t")
        if port is not None:
            command.extend(("-p", str(port)))
        command.append(destination)
        if remote_command is not None:
            command.extend(("--", remote_command))

        return command

    def get_agent_keys(self) -> dict[str, PublicKey]:
        """Return the public keys loaded in the SSH agent, indexed by fingerprint."""

        output = self.app.subprocess.capture([self.agent_path, "-L"], check=False)
        return {key.fingerprint: key for line in output.splitlines() if (key := PublicKey.parse(line)) is not None}

    @staticmethod
    def inspect_public_key_file(path: str | Path) -> PublicKeyFile:
        """Read a single-record public-key selector without consulting the SSH agent."""

        selector_path = Path(path).expand()
        return PublicKeyFile(path=str(selector_path), result=_read_public_key_selector(selector_path))

    @staticmethod
    def resolve_public_key(value: str) -> PublicKey | None:
        """Resolve a public-key literal, public-key file, or companion `.pub` file."""

        if (direct_key := PublicKey.parse(value)) is not None:
            return direct_key
        if not value:
            return None

        path = Path(value).expand()
        candidate_paths = (path,) if path.suffix == ".pub" else (path, Path(f"{path}.pub"))
        for candidate in candidate_paths:
            try:
                if candidate.is_file() and (key := PublicKey.parse(candidate.read_text(encoding="utf-8"))) is not None:
                    return key
            except (OSError, UnicodeError):
                continue

        return None

    def write_host_config(self, hostname: str, options: dict[str, str | list[str]]) -> None:
        """Write a managed host block and ensure that the user's SSH config includes it."""

        config_file = self.config_dir / MANAGED_CONFIG_DIR / hostname
        config_file.parent.ensure_dir()
        config_file.write_text(render_host_config(hostname, options), encoding="utf-8")
        self._ensure_config_inclusion()

    def _ensure_config_inclusion(self) -> None:
        config_file = self.config_dir / "config"
        expected_line = f"Include {MANAGED_CONFIG_DIR}/*"
        lines = config_file.read_text(encoding="utf-8").splitlines() if config_file.exists() else []
        if expected_line in lines:
            return

        new_lines = [expected_line, *lines, ""]
        config_file.parent.ensure_dir()
        config_file.write_text("\n".join(new_lines), encoding="utf-8")


def render_host_config(hostname: str, options: dict[str, str | list[str]]) -> str:
    """Render an SSH config host block, repeating options whose value is a list."""

    lines = [f"Host {hostname}"]
    for key, value in options.items():
        if isinstance(value, list):
            lines.extend(f"    {key} {item}" for item in value)
        else:
            lines.append(f"    {key} {value}")

    lines.append("")
    return "\n".join(lines)


def _read_public_key_selector(path: Path) -> PublicKey | str | None:
    if not path.exists():
        return None
    if not path.is_file():
        return f"`{path}` is not a file."

    try:
        records = [record for line in path.read_text(encoding="utf-8").splitlines() if (record := line.strip())]
    except (OSError, UnicodeError) as error:
        return f"`{path}` could not be read: {error}"

    if len(records) != 1:
        return f"`{path}` must contain exactly one nonempty public-key line."
    if (key := PublicKey.parse(records[0])) is None:
        return f"`{path}` does not contain a valid OpenSSH public key."

    return key
