# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dda.env.dev.git_ssh import write_git_ssh_context
from dda.tools.ssh import PublicKey
from dda.utils.fs import Path
from dda.utils.process import EnvVars

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from dda.cli.application import Application

pytestmark = [pytest.mark.usefixtures("private_storage")]

PERSONAL_AUTHENTICATION_KEY = "ssh-ed25519 cGVyc29uYWwtYXV0aA=="
PERSONAL_SIGNING_KEY = "ssh-ed25519 cGVyc29uYWwtc2lnbg=="
ENTERPRISE_AUTHENTICATION_KEY = "ssh-ed25519 ZW50ZXJwcmlzZS1hdXRo"
ENTERPRISE_SIGNING_KEY = "ssh-ed25519 ZW50ZXJwcmlzZS1zaWdu"
UNLOADED_KEY = "ssh-ed25519 dW5sb2FkZWQ="


def _public_key(value: str) -> PublicKey:
    key = PublicKey.parse(value)
    assert key is not None
    return key


def _write_selector(home: Path, name: str, key: str) -> Path:
    selector = home / ".ssh" / name
    selector.parent.ensure_dir()
    selector.write_text(f"{key} ignored-comment\n", encoding="utf-8")
    return selector


def _mock_discovery(
    app: Application,
    mocker: MockerFixture,
    *,
    home: Path,
    agent_keys: tuple[str, ...],
    git_identities: dict[str, str] | None = None,
) -> MagicMock:
    mocker.patch.object(Path, "home", return_value=home)
    indexed_agent_keys = {_public_key(value).fingerprint: _public_key(value) for value in agent_keys}
    mocker.patch.object(app.tools.ssh, "get_agent_keys", return_value=indexed_agent_keys)
    git_identities = git_identities or {}

    def capture(command: list[str], **_kwargs: object) -> str:
        owner = command[1].removeprefix("remote.__dda.url=https://github.com/").removesuffix("/_dda-profile")
        return git_identities.get(owner, "")

    return mocker.patch.object(app.tools.git, "capture", side_effect=capture)


def test_write_git_ssh_context_generates_complete_identity_configuration(
    app: Application, mocker: MockerFixture, temp_dir: Path
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _write_selector(temp_dir, "ddoghq.pub", ENTERPRISE_AUTHENTICATION_KEY)
    git_capture = _mock_discovery(
        app,
        mocker,
        home=temp_dir,
        agent_keys=(
            PERSONAL_AUTHENTICATION_KEY,
            PERSONAL_SIGNING_KEY,
            ENTERPRISE_AUTHENTICATION_KEY,
            ENTERPRISE_SIGNING_KEY,
        ),
        git_identities={
            "DataDog": (
                f"user.name Host User\nuser.email personal@example.com\nuser.signingkey key::{PERSONAL_SIGNING_KEY}\n"
            ),
            "ddoghq": (
                "user.name Enterprise User\n"
                "user.email user@datadoghq.com\n"
                f"user.signingkey key::{ENTERPRISE_SIGNING_KEY}\n"
            ),
        },
    )
    destination = temp_dir / "context"

    assert write_git_ssh_context(app, destination) is None
    assert (
        (destination / "gitconfig").read_text(encoding="utf-8")
        == """\
[user]
\tname = "Foo Bar"
\temail = "foo@bar.baz"
\tsigningKey = "key::ssh-ed25519 cGVyc29uYWwtc2lnbg=="

[gpg "ssh"]
\tallowedSignersFile = /.shared/git-ssh/allowed_signers

[url "ssh://git@github.com-ddoghq/ddoghq/"]
\tinsteadOf = https://github.com/ddoghq/

[includeIf "hasconfig:remote.*.url:https://github.com/ddoghq/**"]
\tpath = "/.shared/git-ssh/profiles/enterprise.gitconfig"

[url "ssh://git@github.com-ddoghq/ddoghq-"]
\tinsteadOf = https://github.com/ddoghq-

[includeIf "hasconfig:remote.*.url:https://github.com/ddoghq-*/**"]
\tpath = "/.shared/git-ssh/profiles/enterprise.gitconfig"
"""
    )
    assert (
        (destination / "profiles" / "enterprise.gitconfig").read_text(encoding="utf-8")
        == """\
[user]
\tname = "Enterprise User"
\temail = "user@datadoghq.com"
\tsigningKey = "key::ssh-ed25519 ZW50ZXJwcmlzZS1zaWdu"
"""
    )
    assert (
        (destination / "ssh_config").read_text(encoding="utf-8")
        == """\
Host github.com
    HostName github.com
    User git
    IdentityFile /.shared/git-ssh/keys/github-com-auth.pub
    IdentitiesOnly yes

Host github.com-ddoghq
    HostName github.com
    User git
    IdentityFile /.shared/git-ssh/keys/github-com-ddoghq-auth.pub
    IdentitiesOnly yes
"""
    )
    assert (destination / "keys" / "github-com-auth.pub").read_text(
        encoding="utf-8"
    ) == f"{PERSONAL_AUTHENTICATION_KEY}\n"
    assert (destination / "keys" / "github-com-ddoghq-auth.pub").read_text(
        encoding="utf-8"
    ) == f"{ENTERPRISE_AUTHENTICATION_KEY}\n"
    assert (destination / "allowed_signers").read_text(encoding="utf-8") == (
        f'foo@bar.baz namespaces="git" {PERSONAL_SIGNING_KEY}\n'
        f'user@datadoghq.com namespaces="git" {ENTERPRISE_SIGNING_KEY}\n'
    )
    assert {command[1] for command in (call.args[0] for call in git_capture.call_args_list)} == {
        "remote.__dda.url=https://github.com/DataDog/_dda-profile",
        "remote.__dda.url=https://github.com/ddoghq/_dda-profile",
    }


def test_organization_specific_selectors_have_no_effect(
    app: Application, mocker: MockerFixture, temp_dir: Path
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _write_selector(temp_dir, "ddoghq.pub", ENTERPRISE_AUTHENTICATION_KEY)
    for owner, key in (
        ("ddoghq-sandbox", UNLOADED_KEY),
        ("ddoghq-new-org", PERSONAL_AUTHENTICATION_KEY),
        ("ddoghq-invalid", "invalid"),
    ):
        _write_selector(temp_dir, f"{owner}.pub", key)
    _mock_discovery(
        app,
        mocker,
        home=temp_dir,
        agent_keys=(PERSONAL_AUTHENTICATION_KEY, ENTERPRISE_AUTHENTICATION_KEY),
    )
    destination = temp_dir / "context"

    assert write_git_ssh_context(app, destination) is None
    assert (destination / "ssh_config").read_text(encoding="utf-8").count("Host ") == 2
    assert (destination / "keys" / "github-com-ddoghq-auth.pub").read_text(
        encoding="utf-8"
    ) == f"{ENTERPRISE_AUTHENTICATION_KEY}\n"
    assert {path.name for path in (destination / "keys").iterdir()} == {
        "github-com-auth.pub",
        "github-com-ddoghq-auth.pub",
    }


@pytest.mark.parametrize(
    ("owner", "enterprise"),
    [("ddoghq", True), ("ddoghq-sandbox", True), ("ddoghq-new-org", True), ("ddoghqish", False), ("DataDog", False)],
)
def test_git_routes_enterprise_organizations_and_selects_their_signing_profile(
    app: Application, mocker: MockerFixture, temp_dir: Path, owner: str, *, enterprise: bool
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _write_selector(temp_dir, "ddoghq.pub", ENTERPRISE_AUTHENTICATION_KEY)
    git_capture = _mock_discovery(
        app,
        mocker,
        home=temp_dir,
        agent_keys=(PERSONAL_AUTHENTICATION_KEY, ENTERPRISE_AUTHENTICATION_KEY, ENTERPRISE_SIGNING_KEY),
        git_identities={
            "ddoghq": (
                "user.name Enterprise User\n"
                "user.email enterprise@example.com\n"
                f"user.signingkey key::{ENTERPRISE_SIGNING_KEY}\n"
            ),
        },
    )
    destination = temp_dir / "context"
    write_git_ssh_context(app, destination)
    mocker.stop(git_capture)
    gitconfig = destination / "gitconfig"
    gitconfig.write_text(
        gitconfig.read_text(encoding="utf-8").replace("/.shared/git-ssh", destination.as_posix()), encoding="utf-8"
    )
    image_gitconfig = temp_dir / "image.gitconfig"
    image_gitconfig.write_text(
        '[url "ssh://git@github.com/"]\n'
        "\tinsteadOf = https://github.com/\n"
        f'[include]\n\tpath = "{gitconfig.as_posix()}"\n',
        encoding="utf-8",
    )
    repository = temp_dir / "repository"
    repository.ensure_dir()
    url = f"https://github.com/{owner}/repository"

    with EnvVars({"GIT_CONFIG_GLOBAL": str(image_gitconfig), "GIT_CONFIG_NOSYSTEM": "1"}, exclude=["GIT_*"]):
        app.tools.git.capture(["init", "--quiet"], cwd=repository)
        app.tools.git.capture(["remote", "add", "origin", url], cwd=repository)
        remote = app.tools.git.capture(["remote", "get-url", "origin"], cwd=repository).strip()
        stored_url = app.tools.git.capture(["config", "--local", "--get", "remote.origin.url"], cwd=repository).strip()
        name = app.tools.git.capture(["config", "--get", "user.name"], cwd=repository).strip()
        email = app.tools.git.capture(["config", "--get", "user.email"], cwd=repository).strip()
        signing_key = app.tools.git.capture(["config", "--get", "user.signingkey"], cwd=repository).strip()

    assert stored_url == url
    host = "github.com-ddoghq" if enterprise else "github.com"
    assert remote == f"ssh://git@{host}/{owner}/repository"
    assert name == ("Enterprise User" if enterprise else app.config.tools.git.author.name)
    assert email == ("enterprise@example.com" if enterprise else app.config.tools.git.author.email)
    assert signing_key == f"key::{ENTERPRISE_SIGNING_KEY if enterprise else PERSONAL_AUTHENTICATION_KEY}"


@pytest.mark.parametrize("enterprise_selector_exists", [False, True])
def test_unavailable_enterprise_selector_generates_a_personal_context_without_organization_fallback(
    app: Application, mocker: MockerFixture, temp_dir: Path, *, enterprise_selector_exists: bool
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _write_selector(temp_dir, "ddoghq-sandbox.pub", PERSONAL_AUTHENTICATION_KEY)
    if enterprise_selector_exists:
        _write_selector(temp_dir, "ddoghq.pub", ENTERPRISE_AUTHENTICATION_KEY)
    _mock_discovery(
        app,
        mocker,
        home=temp_dir,
        agent_keys=(PERSONAL_AUTHENTICATION_KEY,),
    )
    destination = temp_dir / "context"

    enterprise_error = write_git_ssh_context(app, destination)

    assert enterprise_error is not None
    assert str(temp_dir / ".ssh" / "ddoghq.pub") in enterprise_error
    if enterprise_selector_exists:
        assert _public_key(ENTERPRISE_AUTHENTICATION_KEY).fingerprint in enterprise_error
    else:
        assert "is missing" in enterprise_error
    assert not (destination / "keys" / "github-com-ddoghq-auth.pub").exists()
    assert not (destination / "profiles" / "enterprise.gitconfig").exists()
    gitconfig = (destination / "gitconfig").read_text(encoding="utf-8")
    assert "[includeIf " not in gitconfig
    assert gitconfig.count("\tinsteadOf = ") == 2
    assert "    IdentityAgent none\n" in (destination / "ssh_config").read_text(encoding="utf-8")


def test_unavailable_enterprise_selector_removes_previous_generated_credentials(
    app: Application, mocker: MockerFixture, temp_dir: Path
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    selector = _write_selector(temp_dir, "ddoghq.pub", ENTERPRISE_AUTHENTICATION_KEY)
    _mock_discovery(
        app,
        mocker,
        home=temp_dir,
        agent_keys=(PERSONAL_AUTHENTICATION_KEY, ENTERPRISE_AUTHENTICATION_KEY),
    )
    destination = temp_dir / "context"
    assert write_git_ssh_context(app, destination) is None
    assert (destination / "keys" / "github-com-ddoghq-auth.pub").exists()
    assert (destination / "profiles" / "enterprise.gitconfig").exists()
    selector.unlink()

    assert write_git_ssh_context(app, destination) is not None

    assert not (destination / "keys" / "github-com-ddoghq-auth.pub").exists()
    assert not (destination / "profiles" / "enterprise.gitconfig").exists()


@pytest.mark.parametrize("legacy_selector_exists", [False, True])
def test_personal_selector_is_required(
    app: Application, mocker: MockerFixture, temp_dir: Path, *, legacy_selector_exists: bool
) -> None:
    if legacy_selector_exists:
        _write_selector(temp_dir, "dda.pub", PERSONAL_AUTHENTICATION_KEY)
    _mock_discovery(app, mocker, home=temp_dir, agent_keys=(PERSONAL_AUTHENTICATION_KEY,))

    with pytest.raises(SystemExit):
        write_git_ssh_context(app, temp_dir / "context")

    assert "Required public-key selector" in app.last_error
    assert str(temp_dir / ".ssh" / "dd.pub") in app.last_error


def test_personal_selector_key_must_be_loaded(app: Application, mocker: MockerFixture, temp_dir: Path) -> None:
    selector = _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _mock_discovery(app, mocker, home=temp_dir, agent_keys=(ENTERPRISE_AUTHENTICATION_KEY,))

    with pytest.raises(SystemExit):
        write_git_ssh_context(app, temp_dir / "context")

    assert str(selector) in app.last_error
    assert _public_key(PERSONAL_AUTHENTICATION_KEY).fingerprint in app.last_error
    assert "not loaded in the host SSH agent" in app.last_error


def test_personal_selector_rejects_multiple_records(app: Application, mocker: MockerFixture, temp_dir: Path) -> None:
    selector = _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    selector.write_text(f"{PERSONAL_AUTHENTICATION_KEY}\n{ENTERPRISE_AUTHENTICATION_KEY}\n", encoding="utf-8")
    _mock_discovery(
        app,
        mocker,
        home=temp_dir,
        agent_keys=(PERSONAL_AUTHENTICATION_KEY, ENTERPRISE_AUTHENTICATION_KEY),
    )

    with pytest.raises(SystemExit):
        write_git_ssh_context(app, temp_dir / "context")

    assert "must contain exactly one nonempty public-key line" in app.last_error


def test_personal_and_enterprise_selectors_must_use_distinct_keys(
    app: Application, mocker: MockerFixture, temp_dir: Path
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _write_selector(temp_dir, "ddoghq.pub", PERSONAL_AUTHENTICATION_KEY)
    _mock_discovery(app, mocker, home=temp_dir, agent_keys=(PERSONAL_AUTHENTICATION_KEY,))

    with pytest.raises(SystemExit):
        write_git_ssh_context(app, temp_dir / "context")

    assert "SSH selectors use the same key" in app.last_error
    assert _public_key(PERSONAL_AUTHENTICATION_KEY).fingerprint in app.last_error


def test_configured_signing_key_must_be_loaded(app: Application, mocker: MockerFixture, temp_dir: Path) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _mock_discovery(
        app,
        mocker,
        home=temp_dir,
        agent_keys=(PERSONAL_AUTHENTICATION_KEY,),
        git_identities={
            "DataDog": f"user.email personal@example.com\nuser.signingkey key::{UNLOADED_KEY}\n",
        },
    )

    with pytest.raises(SystemExit):
        write_git_ssh_context(app, temp_dir / "context")

    assert "Git profile `DataDog` selects signing key" in app.last_error
    assert _public_key(UNLOADED_KEY).fingerprint in app.last_error
    assert "not loaded in the host SSH agent" in app.last_error


@pytest.mark.parametrize(("owner", "signing_key"), [("DataDog", "invalid"), ("ddoghq", "")])
def test_invalid_configured_signing_key_never_falls_back_to_authentication_key(
    app: Application, mocker: MockerFixture, temp_dir: Path, owner: str, signing_key: str
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _write_selector(temp_dir, "ddoghq.pub", ENTERPRISE_AUTHENTICATION_KEY)
    _mock_discovery(
        app,
        mocker,
        home=temp_dir,
        agent_keys=(PERSONAL_AUTHENTICATION_KEY, ENTERPRISE_AUTHENTICATION_KEY),
        git_identities={owner: f"user.signingkey {signing_key}\n"},
    )
    destination = temp_dir / "context"

    with pytest.raises(SystemExit):
        write_git_ssh_context(app, destination)

    assert f"configures user.signingKey as `{signing_key}`" in app.last_error
    assert "no public key could be read" in app.last_error
    assert not destination.exists()


def test_host_agent_must_contain_a_key(app: Application, mocker: MockerFixture, temp_dir: Path) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_AUTHENTICATION_KEY)
    _mock_discovery(app, mocker, home=temp_dir, agent_keys=())

    with pytest.raises(SystemExit):
        write_git_ssh_context(app, temp_dir / "context")

    assert "host SSH agent has no loaded public keys" in app.last_error
