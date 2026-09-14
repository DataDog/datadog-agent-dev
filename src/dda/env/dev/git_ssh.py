# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec

from dda.env.dev.interface import DEFAULT_GITHUB_OWNER, ENTERPRISE_GITHUB_OWNER
from dda.tools.ssh import PublicKey, render_host_config
from dda.utils.fs import Path, temp_directory

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.tools.ssh import PublicKeyFile


PERSONAL_SELECTOR_FILE = "dd.pub"
ENTERPRISE_SELECTOR_FILE = f"{ENTERPRISE_GITHUB_OWNER}.pub"
CONTEXT_DIR_NAME = "git-ssh"
CONTAINER_CONTEXT_ROOT = f"/.shared/{CONTEXT_DIR_NAME}"
PERSONAL_ALIAS = "github.com"
ENTERPRISE_ALIAS = f"github.com-{ENTERPRISE_GITHUB_OWNER}"


class DeveloperSSHIdentities(msgspec.Struct, frozen=True):
    """The conventional SSH identities used by developer environments."""

    agent_keys: dict[str, PublicKey]
    personal: PublicKeyFile
    enterprise: PublicKeyFile

    @property
    def cross_account_duplicate_error(self) -> str | None:
        personal_key = self.personal.result
        enterprise_key = self.enterprise.result
        if (
            not isinstance(personal_key, PublicKey)
            or not isinstance(enterprise_key, PublicKey)
            or personal_key.fingerprint != enterprise_key.fingerprint
        ):
            return None

        return (
            "Personal and Enterprise SSH selectors use the same key "
            f"{personal_key.fingerprint}. Select a distinct enterprise key."
        )


class GitSSHProfile(msgspec.Struct, frozen=True):
    """A complete authentication and signing profile resolved against the host agent snapshot."""

    name: str
    email: str
    authentication_key: PublicKey
    signing_key: PublicKey


class GitSSHDoctorReport(msgspec.Struct, frozen=True):
    authentication: DeveloperSSHIdentities
    personal: GitSSHProfile | str
    enterprise: GitSSHProfile | str

    @property
    def fatal_errors(self) -> tuple[str, ...]:
        authentication = self.authentication
        agent_keys = authentication.agent_keys
        personal = authentication.personal.resolve(agent_keys, required=True)
        errors: list[str] = []
        if not agent_keys:
            errors.append(
                "The host SSH agent has no loaded public keys. Start the agent and load the personal GitHub key "
                f"selected by `{authentication.personal.path}`."
            )
        if isinstance(personal, str):
            errors.append(personal)
        if (duplicate_error := authentication.cross_account_duplicate_error) is not None:
            errors.append(duplicate_error)
        if isinstance(personal, PublicKey) and isinstance(self.personal, str):
            errors.append(self.personal)
        if isinstance(authentication.enterprise.resolve(agent_keys), PublicKey) and isinstance(self.enterprise, str):
            errors.append(self.enterprise)
        return tuple(errors)


def inspect_git_ssh(app: Application) -> GitSSHDoctorReport:
    ssh_dir = app.tools.ssh.config_dir
    authentication = DeveloperSSHIdentities(
        agent_keys=app.tools.ssh.get_agent_keys(),
        personal=app.tools.ssh.inspect_public_key_file(ssh_dir / PERSONAL_SELECTOR_FILE),
        enterprise=app.tools.ssh.inspect_public_key_file(ssh_dir / ENTERPRISE_SELECTOR_FILE),
    )
    return GitSSHDoctorReport(
        authentication=authentication,
        personal=_inspect_git_profile(
            app, DEFAULT_GITHUB_OWNER, authentication.personal, authentication.agent_keys, required=True
        ),
        enterprise=_inspect_git_profile(
            app, ENTERPRISE_GITHUB_OWNER, authentication.enterprise, authentication.agent_keys
        ),
    )


def write_git_ssh_context(app: Application, destination: Path) -> str | None:
    report = inspect_git_ssh(app)
    personal_identity = report.personal
    fatal_errors = report.fatal_errors
    if isinstance(personal_identity, str) or fatal_errors:
        app.abort("\n".join(fatal_errors))
    enterprise_identity = report.enterprise if isinstance(report.enterprise, GitSSHProfile) else None

    keys_dir = destination / "keys"
    profiles_dir = destination / "profiles"
    keys_dir.ensure_dir()
    profiles_dir.ensure_dir()

    git_config_blocks = [
        _render_identity(personal_identity),
        f'[gpg "ssh"]\n\tallowedSignersFile = {CONTAINER_CONTEXT_ROOT}/allowed_signers\n',
    ]
    enterprise_profile_path = profiles_dir / "enterprise.gitconfig"
    container_profile_path = f"{CONTAINER_CONTEXT_ROOT}/profiles/{enterprise_profile_path.name}"
    if enterprise_identity is None:
        enterprise_profile_path.unlink(missing_ok=True)
    else:
        enterprise_profile_path.write_atomic(
            _render_identity(enterprise_identity),
            "w",
            encoding="utf-8",
            newline="\n",
        )

    for owner_prefix, owner_pattern in (
        (f"{ENTERPRISE_GITHUB_OWNER}/", ENTERPRISE_GITHUB_OWNER),
        (f"{ENTERPRISE_GITHUB_OWNER}-", f"{ENTERPRISE_GITHUB_OWNER}-*"),
    ):
        git_config_blocks.append(
            f'[url "ssh://git@{ENTERPRISE_ALIAS}/{owner_prefix}"]\n\tinsteadOf = https://github.com/{owner_prefix}\n'
        )
        if enterprise_identity is not None:
            git_config_blocks.append(
                f'[includeIf "hasconfig:remote.*.url:https://github.com/{owner_pattern}/**"]\n'
                f"\tpath = {_quote_git_value(container_profile_path)}\n"
            )

    ssh_config = "\n".join((
        _render_ssh_host(PERSONAL_ALIAS, personal_identity.authentication_key, keys_dir),
        _render_ssh_host(
            ENTERPRISE_ALIAS,
            enterprise_identity.authentication_key if enterprise_identity is not None else None,
            keys_dir,
        ),
    ))

    identities = (personal_identity,) if enterprise_identity is None else (personal_identity, enterprise_identity)
    allowed_signers = {
        f'{identity.email} namespaces="git" {identity.signing_key.line}' for identity in identities if identity.email
    }
    (destination / "gitconfig").write_atomic(
        "\n".join(git_config_blocks).rstrip() + "\n", "w", encoding="utf-8", newline="\n"
    )
    (destination / "ssh_config").write_atomic(ssh_config, "w", encoding="utf-8", newline="\n")
    (destination / "allowed_signers").write_atomic(
        "\n".join(sorted(allowed_signers)) + ("\n" if allowed_signers else ""),
        "w",
        encoding="utf-8",
        newline="\n",
    )

    return report.enterprise if isinstance(report.enterprise, str) else None


def _inspect_git_profile(
    app: Application,
    owner: str,
    selector: PublicKeyFile,
    agent_keys: dict[str, PublicKey],
    *,
    required: bool = False,
) -> GitSSHProfile | str:
    authentication_key = selector.resolve(agent_keys, required=required)
    if isinstance(authentication_key, str):
        return authentication_key
    with temp_directory() as work_dir:
        # The synthetic remote makes Git evaluate URL-based conditional includes without contacting GitHub.
        output = app.tools.git.capture(
            [
                "-c",
                f"remote.__dda.url=https://github.com/{owner}/_dda-profile",
                "config",
                "--get-regexp",
                r"^user\.(name|email|signingkey)$",
            ],
            cwd=work_dir,
            check=False,
        )

    values: dict[str, str] = {}
    for line in output.splitlines():
        key, _, value = line.partition(" ")
        values[key.casefold()] = value

    profile = "enterprise" if owner == ENTERPRISE_GITHUB_OWNER else owner
    configured_signing_key = values.get("user.signingkey")
    if configured_signing_key is None:
        signing_key = authentication_key
    else:
        resolved_signing_key = app.tools.ssh.resolve_public_key(configured_signing_key)
        if resolved_signing_key is None:
            return (
                f"Git profile `{profile}` configures user.signingKey as `{configured_signing_key}`, but no "
                "public key could be read from that value or its companion `.pub` file."
            )
        signing_key = resolved_signing_key
        if signing_key.fingerprint not in agent_keys:
            return (
                f"Git profile `{profile}` selects signing key {signing_key.fingerprint}, but that key is not "
                "loaded in the host SSH agent."
            )

    name = values.get("user.name", "")
    email = values.get("user.email", "")
    if owner == DEFAULT_GITHUB_OWNER:
        name = app.config.tools.git.author.name or name
        email = app.config.tools.git.author.email or email
    return GitSSHProfile(
        name=name,
        email=email,
        authentication_key=authentication_key,
        signing_key=signing_key,
    )


def _render_identity(identity: GitSSHProfile) -> str:
    lines = ["[user]"]
    if identity.name:
        lines.append(f"\tname = {_quote_git_value(identity.name)}")
    if identity.email:
        lines.append(f"\temail = {_quote_git_value(identity.email)}")
    lines.append(f"\tsigningKey = {_quote_git_value(f'key::{identity.signing_key.line}')}")
    return "\n".join(lines) + "\n"


def _render_ssh_host(alias: str, key: PublicKey | None, keys_dir: Path) -> str:
    key_path = keys_dir / f"{alias.replace('.', '-')}-auth.pub"
    options: dict[str, str | list[str]] = {"HostName": "github.com", "User": "git"}
    if key is None:
        key_path.unlink(missing_ok=True)
        options["IdentityAgent"] = "none"
        options["IdentityFile"] = "none"
    else:
        key_path.write_atomic(f"{key.line}\n", "w", encoding="utf-8", newline="\n")
        options["IdentityFile"] = f"{CONTAINER_CONTEXT_ROOT}/keys/{key_path.name}"
    options["IdentitiesOnly"] = "yes"
    return render_host_config(alias, options)


def _quote_git_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
    return f'"{escaped}"'
