# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.env.dev.git_ssh import GitSSHProfile
    from dda.tools.ssh import PublicKey, PublicKeyFile


@dynamic_command(short_help="Diagnose developer-environment SSH identities")
@pass_app
def cmd(app: Application) -> None:
    """Diagnose the SSH authentication and signing identities used by developer environments."""
    from dda.env.dev.git_ssh import inspect_git_ssh
    from dda.env.dev.ssh_migration import migrate_legacy_personal_key

    # TODO: Remove this migration after users have transitioned from dda.pub to dd.pub.
    migrate_legacy_personal_key(app)
    report = inspect_git_ssh(app)
    lines: list[str] = []
    for name, identity, signing in (
        ("Personal", report.authentication.personal, report.personal),
        ("Enterprise", report.authentication.enterprise, report.enterprise),
    ):
        if lines:
            lines.append("")
        lines.extend((
            name,
            f"  Selector: {identity.path}",
            f"  Authentication: {_authentication_status(identity, report.authentication.agent_keys)}",
            f"  Signing: {_signing_status(signing, identity, report.authentication.agent_keys)}",
        ))

    fatal_errors = report.fatal_errors
    lines.append("")
    if fatal_errors:
        lines.extend(("Status: error", "", "Problems:"))
        lines.extend(f"  - {error}" for error in fatal_errors)
    elif isinstance(report.enterprise, str):
        lines.append("Status: personal identity ready; enterprise access unavailable")
    else:
        lines.append("Status: ready")
    app.display("\n".join(lines))

    if fatal_errors:
        app.abort(code=1)


def _authentication_status(identity: PublicKeyFile, agent_keys: dict[str, PublicKey]) -> str:
    key = identity.result
    if key is None or isinstance(key, str):
        return f"unavailable ({identity.resolve(agent_keys)})"
    state = "loaded" if key.fingerprint in agent_keys else "not loaded"
    return f"{key.fingerprint} ({state})"


def _signing_status(
    profile: GitSSHProfile | str,
    authentication: PublicKeyFile,
    agent_keys: dict[str, PublicKey],
) -> str:
    if isinstance(authentication.resolve(agent_keys), str):
        return "unavailable"
    if isinstance(profile, str):
        return f"unavailable ({profile})"
    return f"{profile.signing_key.fingerprint} (loaded)"
