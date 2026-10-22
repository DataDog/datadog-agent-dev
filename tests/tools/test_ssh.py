# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dda.tools.ssh import PublicKey, PublicKeyFile
from dda.utils.fs import Path

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from dda.cli.application import Application

pytestmark = [pytest.mark.usefixtures("private_storage")]

PUBLIC_KEY = "ssh-ed25519 cGVyc29uYWwtYXV0aA=="
SECOND_PUBLIC_KEY = "ssh-ed25519 ZW50ZXJwcmlzZS1hdXRo"


def _public_key(value: str) -> PublicKey:
    key = PublicKey.parse(value)
    assert key is not None
    return key


def test_execution_context(app: Application) -> None:
    app.tools.ssh.path = "ssh"

    with app.tools.ssh.execution_context(["-G", "example.com"]) as context:
        assert context.command == ["ssh", "-G", "example.com"]
        assert context.env_vars == {}


@pytest.mark.parametrize("port", [pytest.param(22, id="int port"), pytest.param("22", id="str port")])
def test_get_command(app: Application, port: int | str) -> None:
    app.tools.ssh.path = "ssh"

    assert app.tools.ssh.get_command(
        "host",
        port=port,
        forward_agent=True,
        quiet=True,
        allocate_tty=True,
        remote_command="uname -a",
    ) == [
        "ssh",
        "-A",
        "-q",
        "-t",
        "-p",
        str(port),
        "host",
        "--",
        "uname -a",
    ]


def test_get_command_uses_openssh_defaults_when_options_are_absent(app: Application) -> None:
    app.tools.ssh.path = "ssh"

    assert app.tools.ssh.get_command("host") == ["ssh", "host"]
    assert app.tools.ssh.get_command("host", forward_agent=False) == ["ssh", "-a", "host"]


def test_get_agent_keys_deduplicates_fingerprints(app: Application, mocker: MockerFixture) -> None:
    app.tools.ssh.agent_path = "ssh-add"
    capture = mocker.patch.object(
        app.subprocess,
        "capture",
        return_value=f"{PUBLIC_KEY} first\ninvalid\n{PUBLIC_KEY} duplicate\n{SECOND_PUBLIC_KEY}\n",
    )

    keys = app.tools.ssh.get_agent_keys()

    assert set(keys.values()) == {
        PublicKey.parse(PUBLIC_KEY),
        PublicKey.parse(SECOND_PUBLIC_KEY),
    }
    capture.assert_called_once_with(["ssh-add", "-L"], check=False)


def test_inspect_public_key_file_accepts_one_record_with_a_comment(app: Application, temp_dir: Path) -> None:
    selector = temp_dir / "identity.pub"
    selector.write_text(f"{PUBLIC_KEY} user@example.com\n", encoding="utf-8")
    key = _public_key(PUBLIC_KEY)

    result = app.tools.ssh.inspect_public_key_file(selector)

    assert result == PublicKeyFile(path=str(selector), result=key)
    assert result.resolve({key.fingerprint: key}) == key


def test_inspect_public_key_file_reports_missing_and_unloaded_selectors(app: Application, temp_dir: Path) -> None:
    missing = temp_dir / "missing.pub"
    selector = temp_dir / "identity.pub"
    selector.write_text(PUBLIC_KEY, encoding="utf-8")
    key = _public_key(PUBLIC_KEY)

    missing_result = app.tools.ssh.inspect_public_key_file(missing)
    unloaded_result = app.tools.ssh.inspect_public_key_file(selector)

    assert missing_result == PublicKeyFile(path=str(missing), result=None)
    assert missing_result.resolve({}) == f"Public-key selector `{missing}` is missing."
    assert unloaded_result == PublicKeyFile(path=str(selector), result=key)
    assert unloaded_result.resolve({}) == (
        f"Public-key selector `{selector}` selects {key.fingerprint}, but that key is not loaded in the host SSH agent."
    )


@pytest.mark.parametrize(
    ("contents", "error"),
    [
        ("", "must contain exactly one nonempty public-key line"),
        (f"{PUBLIC_KEY}\n{SECOND_PUBLIC_KEY}\n", "must contain exactly one nonempty public-key line"),
        ("not a key\n", "does not contain a valid OpenSSH public key"),
    ],
)
def test_inspect_public_key_file_rejects_invalid_selectors(
    app: Application, temp_dir: Path, contents: str, error: str
) -> None:
    selector = temp_dir / "identity.pub"
    selector.write_text(contents, encoding="utf-8")

    result = app.tools.ssh.inspect_public_key_file(selector)

    assert isinstance(result.result, str)
    assert error in result.result


def test_resolve_public_key(app: Application, temp_dir: Path) -> None:
    private_key = temp_dir / "identity"
    public_key = temp_dir / "identity.pub"
    public_key.write_text(PUBLIC_KEY, encoding="utf-8")
    direct_public_key = temp_dir / "selector"
    direct_public_key.write_text(SECOND_PUBLIC_KEY, encoding="utf-8")

    assert app.tools.ssh.resolve_public_key(f"key::{PUBLIC_KEY}") == PublicKey.parse(PUBLIC_KEY)
    assert app.tools.ssh.resolve_public_key(str(private_key)) == PublicKey.parse(PUBLIC_KEY)
    assert app.tools.ssh.resolve_public_key(str(direct_public_key)) == PublicKey.parse(SECOND_PUBLIC_KEY)
    assert app.tools.ssh.resolve_public_key(str(temp_dir / "missing")) is None
    assert app.tools.ssh.resolve_public_key("not a public key") is None


def test_write_host_config_is_included_once(app: Application, mocker: MockerFixture, temp_dir: Path) -> None:
    mocker.patch.object(Path, "home", return_value=temp_dir)
    ssh_config = Path.home() / ".ssh" / "config"
    ssh_config.parent.ensure_dir()
    ssh_config.write_text("Host existing\n    User example\n", encoding="utf-8")
    options: dict[str, str | list[str]] = {"foo": "bar", "baz": "qux", "multi": ["a", "b", "c"]}

    app.tools.ssh.write_host_config("localhost", options)
    app.tools.ssh.write_host_config("localhost", options)

    managed_config = Path.home() / ".ssh" / ".dda" / "localhost"
    assert (
        managed_config.read_text()
        == """\
Host localhost
    foo bar
    baz qux
    multi a
    multi b
    multi c
"""
    )
    assert (
        ssh_config.read_text()
        == """\
Include .dda/*
Host existing
    User example
"""
    )
