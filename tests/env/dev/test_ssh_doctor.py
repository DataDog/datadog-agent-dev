# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dda.tools.ssh import PublicKey
from dda.utils.fs import Path
from dda.utils.process import EnvVars

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import ModuleType

    from pytest_mock import MockerFixture

    from dda.cli.application import Application
    from tests.conftest import CliRunner

PERSONAL_KEY = "ssh-ed25519 cGVyc29uYWwtYXV0aA=="
ENTERPRISE_KEY = "ssh-ed25519 ZW50ZXJwcmlzZS1hdXRo"


def _public_key(value: str) -> PublicKey:
    key = PublicKey.parse(value)
    assert key is not None
    return key


def _write_selector(home: Path, name: str, key: str) -> Path:
    path = home / ".ssh" / name
    path.parent.ensure_dir()
    path.write_text(f"{key}\n", encoding="utf-8")
    return path


def _key_files(home: Path) -> dict[str, bytes]:
    return {
        name: path.read_bytes()
        for name in ("dda", "dda.pub", "dd", "dd.pub")
        if (path := home / ".ssh" / name).exists()
    }


def _mock_inspection(mocker: MockerFixture, home: Path, *agent_keys: str, mock_git: bool = True) -> None:
    mocker.patch.object(Path, "home", return_value=home)
    keys = {_public_key(value).fingerprint: _public_key(value) for value in agent_keys}
    mocker.patch("dda.tools.ssh.SSH.get_agent_keys", return_value=keys)
    if mock_git:
        mocker.patch("dda.tools.git.Git.capture", return_value="")


@pytest.mark.parametrize("enterprise_loaded", [False, True])
def test_ssh_doctor_reports_identity_readiness(
    dda: CliRunner, helpers: ModuleType, mocker: MockerFixture, temp_dir: Path, *, enterprise_loaded: bool
) -> None:
    personal_selector = _write_selector(temp_dir, "dd.pub", PERSONAL_KEY)
    enterprise_selector = _write_selector(temp_dir, "ddoghq.pub", ENTERPRISE_KEY)
    agent_keys = (PERSONAL_KEY, ENTERPRISE_KEY) if enterprise_loaded else (PERSONAL_KEY,)
    _mock_inspection(mocker, temp_dir, *agent_keys)
    personal_fingerprint = _public_key(PERSONAL_KEY).fingerprint
    enterprise_fingerprint = _public_key(ENTERPRISE_KEY).fingerprint
    enterprise_state = "loaded" if enterprise_loaded else "not loaded"
    enterprise_signing = f"{enterprise_fingerprint} (loaded)" if enterprise_loaded else "unavailable"
    status = "ready" if enterprise_loaded else "personal identity ready; enterprise access unavailable"

    result = dda("env", "dev", "ssh", "doctor")

    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            Personal
              Selector: {personal_selector}
              Authentication: {personal_fingerprint} (loaded)
              Signing: {personal_fingerprint} (loaded)

            Enterprise
              Selector: {enterprise_selector}
              Authentication: {enterprise_fingerprint} ({enterprise_state})
              Signing: {enterprise_signing}

            Status: {status}
            """
        ),
    )


def test_ssh_doctor_reports_required_personal_selector_failure(
    dda: CliRunner, helpers: ModuleType, mocker: MockerFixture, temp_dir: Path
) -> None:
    personal_selector = temp_dir / ".ssh" / "dd.pub"
    enterprise_selector = temp_dir / ".ssh" / "ddoghq.pub"
    _mock_inspection(mocker, temp_dir, PERSONAL_KEY)

    result = dda("env", "dev", "ssh", "doctor")

    result.check(
        exit_code=1,
        stdout=helpers.dedent(
            f"""
            Personal
              Selector: {personal_selector}
              Authentication: unavailable (Public-key selector `{personal_selector}` is missing.)
              Signing: unavailable

            Enterprise
              Selector: {enterprise_selector}
              Authentication: unavailable (Public-key selector `{enterprise_selector}` is missing.)
              Signing: unavailable

            Status: error

            Problems:
              - Required public-key selector `{personal_selector}` is missing.
            """
        ),
    )


@pytest.mark.parametrize("selector_contents", [None, "invalid", f"{ENTERPRISE_KEY}\n{ENTERPRISE_KEY}"])
def test_ssh_doctor_explains_unavailable_enterprise_selector(
    dda: CliRunner, mocker: MockerFixture, temp_dir: Path, selector_contents: str | None
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_KEY)
    if selector_contents is not None:
        _write_selector(temp_dir, "ddoghq.pub", selector_contents)
    _mock_inspection(mocker, temp_dir, PERSONAL_KEY)

    result = dda("env", "dev", "ssh", "doctor")

    result.check_exit_code(0)
    assert "Status: personal identity ready; enterprise access unavailable" in result.stdout
    reason = (
        "is missing" if selector_contents is None else "must contain" if "\n" in selector_contents else "valid OpenSSH"
    )
    assert reason in result.stdout


@pytest.fixture
def legacy_identity(mocker: MockerFixture, temp_dir: Path) -> Generator[Path, None, None]:
    _write_selector(temp_dir, "dda.pub", PERSONAL_KEY)
    (temp_dir / ".ssh" / "dda").write_bytes(b"existing private key")
    config = temp_dir / ".gitconfig"
    config.write_text("", encoding="utf-8")
    _mock_inspection(mocker, temp_dir, PERSONAL_KEY, mock_git=False)
    with EnvVars({
        "GIT_CONFIG_GLOBAL": str(config),
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(temp_dir),
        "USERPROFILE": str(temp_dir),
    }):
        yield temp_dir


def test_ssh_doctor_reports_invalid_signing_configuration(
    dda: CliRunner, mocker: MockerFixture, temp_dir: Path
) -> None:
    _write_selector(temp_dir, "dd.pub", PERSONAL_KEY)
    _write_selector(temp_dir, "ddoghq.pub", ENTERPRISE_KEY)
    _mock_inspection(mocker, temp_dir, PERSONAL_KEY, ENTERPRISE_KEY)
    mocker.patch("dda.tools.git.Git.capture", return_value="user.signingkey invalid\n")

    result = dda("env", "dev", "ssh", "doctor")

    result.check_exit_code(1)
    for profile in ("DataDog", "enterprise"):
        assert f"Signing: unavailable (Git profile `{profile}` configures user.signingKey as `invalid`" in result.stdout
    assert "Status: error" in result.stdout


def test_ssh_doctor_migrates_keys_and_configuration(dda: CliRunner, legacy_identity: Path, app: Application) -> None:
    home = legacy_identity
    ssh_dir = home / ".ssh"
    config = home / ".gitconfig"
    config.write_text(
        '[user]\n\tsigningKey = "~/.ssh/dda"\n[includeIf "gitdir:/inactive/"]\n\tpath = inactive.gitconfig\n',
        encoding="utf-8",
    )
    included = home / "inactive.gitconfig"
    included.write_text('[user]\n\tsigningKey = "~/.ssh/dda.pub"\n[include]\n\tpath = .gitconfig\n', encoding="utf-8")
    (ssh_dir / "config").write_bytes(
        b'Include profiles/*.conf\r\nHost github.com\r\n\tIdentityFile "~/.ssh/dda" # personal\r\n'
        b"Host enterprise\r\n\tIdentityFile ~/.ssh/ddoghq\r\n"
    )
    profiles = ssh_dir / "profiles"
    profiles.ensure_dir()
    (profiles / "personal.conf").write_text(
        'Include config\nHost personal\n\tIdentityFile="~/.ssh/dda.pub"\n\tIdentityFile="${DDA_LEGACY_KEY}"\n',
        encoding="utf-8",
    )

    with EnvVars({"DDA_LEGACY_KEY": str(ssh_dir / "dda")}):
        result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(0)
    preview, _, _ = result.stdout.partition("Migrate? [y/N]:")
    assert preview.startswith(f"Found `{ssh_dir / 'dda.pub'}`.\n")
    assert f"Update Git user.signingKey in `{config}` from `~/.ssh/dda` to `~/.ssh/dd`." in preview
    assert f"Update Git user.signingKey in `{included}` from `~/.ssh/dda.pub` to `~/.ssh/dd.pub`." in preview
    assert f"Update SSH IdentityFile references in `{ssh_dir / 'config'}`." in preview
    assert f"Update SSH IdentityFile references in `{profiles / 'personal.conf'}`." in preview
    assert "Load " not in preview
    assert "Migrated the personal SSH key" in result.stdout
    assert "Status: personal identity ready" in result.stdout
    assert (ssh_dir / "dd").read_bytes() == b"existing private key"
    assert (ssh_dir / "dd.pub").read_text() == f"{PERSONAL_KEY}\n"
    assert not (ssh_dir / "dda").exists()
    assert not (ssh_dir / "dda.pub").exists()
    assert app.tools.git.capture(["config", "--file", str(config), "--get", "user.signingkey"]).strip() == "~/.ssh/dd"
    assert (
        app.tools.git.capture(["config", "--file", str(included), "--get", "user.signingkey"]).strip()
        == "~/.ssh/dd.pub"
    )
    assert (ssh_dir / "config").read_bytes() == (
        b'Include profiles/*.conf\r\nHost github.com\r\n\tIdentityFile "~/.ssh/dd" # personal\r\n'
        b"Host enterprise\r\n\tIdentityFile ~/.ssh/ddoghq\r\n"
    )
    assert 'IdentityFile="~/.ssh/dd.pub"' in (profiles / "personal.conf").read_text()
    assert f'IdentityFile="{ssh_dir / "dd"}"' in (profiles / "personal.conf").read_text()


@pytest.mark.parametrize("answer", ["n\n", "\n"])
def test_ssh_doctor_declining_migration_keeps_old_files(dda: CliRunner, legacy_identity: Path, answer: str) -> None:
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input=answer)

    result.check_exit_code(1)
    assert f"Rename `{legacy_identity / '.ssh' / 'dda'}` to `{legacy_identity / '.ssh' / 'dd'}`." in result.stdout
    assert "Migrate? [y/N]:" in result.stdout
    assert "Update Git" not in result.stdout
    assert "Update SSH" not in result.stdout
    assert "Load " not in result.stdout
    assert _key_files(legacy_identity) == original_keys
    assert "Required public-key selector" in result.stdout


def test_ssh_doctor_does_not_prompt_noninteractively(dda: CliRunner, legacy_identity: Path) -> None:
    original_keys = _key_files(legacy_identity)

    result = dda("--no-interactive", "env", "dev", "ssh", "doctor")

    result.check_exit_code(1)
    assert "dda env dev ssh doctor" in result.stdout
    assert "[y/N]" not in result.stdout
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_existing_selector_does_not_offer_migration(dda: CliRunner, legacy_identity: Path) -> None:
    _write_selector(legacy_identity, "dd.pub", PERSONAL_KEY)
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor")

    result.check_exit_code(0)
    assert "Rename" not in result.stdout
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_migration_refuses_existing_private_key(dda: CliRunner, legacy_identity: Path) -> None:
    private = legacy_identity / ".ssh" / "dd"
    private.write_bytes(b"another private key")
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(1)
    assert "Refusing to overwrite" in result.output
    assert "Migrate?" not in result.stdout
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_migration_rejects_invalid_public_key(dda: CliRunner, legacy_identity: Path) -> None:
    _write_selector(legacy_identity, "dda.pub", "invalid")
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(1)
    assert "does not contain a valid OpenSSH public key" in result.output
    assert "Migrate?" not in result.stdout
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_migrates_public_only_identity_loaded_in_agent(
    dda: CliRunner, legacy_identity: Path, app: Application
) -> None:
    (legacy_identity / ".ssh" / "dda").unlink()
    config = legacy_identity / ".gitconfig"
    config.write_text('[user]\n\tsigningKey = "~/.ssh/dda"\n', encoding="utf-8")

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(0)
    preview, _, _ = result.stdout.partition("Migrate? [y/N]:")
    assert f"Rename `{legacy_identity / '.ssh' / 'dda.pub'}` to `{legacy_identity / '.ssh' / 'dd.pub'}`." in preview
    assert f"Rename `{legacy_identity / '.ssh' / 'dda'}`" not in preview
    assert "Load " not in preview
    assert (legacy_identity / ".ssh" / "dd.pub").is_file()
    assert not (legacy_identity / ".ssh" / "dd").exists()
    assert not (legacy_identity / ".ssh" / "dda.pub").exists()
    assert app.tools.git.capture(["config", "--file", str(config), "--get", "user.signingkey"]).strip() == "~/.ssh/dd"
    assert "Status: personal identity ready" in result.stdout


def test_ssh_doctor_migration_loads_only_missing_personal_key(
    dda: CliRunner, legacy_identity: Path, mocker: MockerFixture
) -> None:
    from subprocess import CompletedProcess

    _write_selector(legacy_identity, "ddoghq.pub", ENTERPRISE_KEY)
    personal_key = _public_key(PERSONAL_KEY)
    enterprise_key = _public_key(ENTERPRISE_KEY)
    all_keys = {key.fingerprint: key for key in (personal_key, enterprise_key)}
    mocker.patch(
        "dda.tools.ssh.SSH.get_agent_keys",
        side_effect=[{enterprise_key.fingerprint: enterprise_key}, all_keys, all_keys],
    )
    mocker.patch("dda.tools.git.Git.capture", return_value="")
    attach = mocker.patch("dda.utils.process.SubprocessRunner.attach", return_value=CompletedProcess([], 0))

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(0)
    preview, _, _ = result.stdout.partition("Migrate? [y/N]:")
    assert f"Load {personal_key.fingerprint} into the host SSH agent" in preview
    assert "Status: ready" in result.stdout
    attach.assert_called_once_with(
        [mocker.ANY, str(legacy_identity / ".ssh" / "dda")], check=False, abort_on_error=False
    )
    assert (legacy_identity / ".ssh" / "dd").is_file()
    assert (legacy_identity / ".ssh" / "dd.pub").is_file()
    assert (legacy_identity / ".ssh" / "ddoghq.pub").read_text() == f"{ENTERPRISE_KEY}\n"


@pytest.mark.parametrize("exit_code", [0, 1])
def test_ssh_doctor_migration_keeps_files_when_agent_does_not_load_key(
    dda: CliRunner, legacy_identity: Path, mocker: MockerFixture, exit_code: int
) -> None:
    from subprocess import CompletedProcess

    mocker.patch("dda.tools.ssh.SSH.get_agent_keys", return_value={})
    mocker.patch("dda.tools.git.Git.capture", return_value="")
    mocker.patch("dda.utils.process.SubprocessRunner.attach", return_value=CompletedProcess([], exit_code))
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(1)
    assert "could not be loaded" in result.output
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_announces_legacy_key_before_agent_inspection(
    legacy_identity: Path, app: Application, mocker: MockerFixture
) -> None:
    from dda.env.dev.ssh_migration import migrate_legacy_personal_key

    app.console.is_interactive = True
    display = mocker.spy(app, "display")
    confirm = mocker.patch.object(app, "confirm", return_value=False)
    key = _public_key(PERSONAL_KEY)

    def inspect_agent():
        assert display.call_args_list[0] == mocker.call(f"Found `{legacy_identity / '.ssh' / 'dda.pub'}`.")
        return {key.fingerprint: key}

    inspect = mocker.patch.object(app.tools.ssh, "get_agent_keys", side_effect=inspect_agent)
    original_keys = _key_files(legacy_identity)

    migrate_legacy_personal_key(app)

    inspect.assert_called_once()
    confirm.assert_called_once_with("Migrate?", default=False)
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_migration_preview_does_not_load_keys_or_edit_configuration(
    dda: CliRunner, legacy_identity: Path, mocker: MockerFixture
) -> None:
    from dda.utils.process import SubprocessRunner

    config = legacy_identity / ".gitconfig"
    git_contents = b'[user]\n\tsigningKey = "~/.ssh/dda"\n'
    config.write_bytes(git_contents)
    ssh_config = legacy_identity / ".ssh" / "config"
    ssh_contents = b"Host github.com\n\tIdentityFile ~/.ssh/dda\n"
    ssh_config.write_bytes(ssh_contents)
    mocker.patch("dda.tools.ssh.SSH.get_agent_keys", return_value={})
    original_attach = SubprocessRunner.attach

    def refuse_agent_changes(self, command, **kwargs):
        if Path(command[0]).stem == "ssh-add":
            pytest.fail("The migration must not load a key before confirmation.")
        return original_attach(self, command, **kwargs)

    mocker.patch.object(SubprocessRunner, "attach", refuse_agent_changes)
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="n\n")

    result.check_exit_code(1)
    preview, _, _ = result.stdout.partition("Migrate? [y/N]:")
    assert f"Load {_public_key(PERSONAL_KEY).fingerprint} into the host SSH agent" in preview
    assert f"Update Git user.signingKey in `{config}`" in preview
    assert f"Update SSH IdentityFile references in `{ssh_config}`" in preview
    assert config.read_bytes() == git_contents
    assert ssh_config.read_bytes() == ssh_contents
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_reports_git_edit_before_later_inspection_failure(dda: CliRunner, legacy_identity: Path) -> None:
    config = legacy_identity / ".gitconfig"
    contents = b'[user]\n\tsigningKey = "~/.ssh/dda"\n'
    config.write_bytes(contents)
    (legacy_identity / ".ssh" / "config").write_text('IdentityFile "', encoding="utf-8")
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor")

    result.check_exit_code(1)
    assert f"Update Git user.signingKey in `{config}` from `~/.ssh/dda` to `~/.ssh/dd`." in result.stdout
    assert "No closing quotation" in result.output
    assert "Migrate?" not in result.stdout
    assert config.read_bytes() == contents
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_migration_requires_agent_key_for_public_only_identity(
    dda: CliRunner, legacy_identity: Path, mocker: MockerFixture
) -> None:
    (legacy_identity / ".ssh" / "dda").unlink()
    mocker.patch("dda.tools.ssh.SSH.get_agent_keys", return_value={})
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(1)
    assert "in the host SSH agent first" in result.output
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_migration_restores_files_when_configuration_update_fails(
    dda: CliRunner, legacy_identity: Path, mocker: MockerFixture
) -> None:
    from dda.tools.git import Git

    config = legacy_identity / ".gitconfig"
    original = b'[user]\r\n\tsigningKey = "~/.ssh/dda"\r\n'
    config.write_bytes(original)
    original_capture = Git.capture

    def fail_after_edit(self, command, **kwargs):
        output = original_capture(self, command, **kwargs)
        if "--replace-all" in command:
            msg = "Configuration update failed."
            raise ValueError(msg)
        return output

    mocker.patch.object(Git, "capture", fail_after_edit)
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(1)
    assert "Configuration update failed" in result.output
    assert config.read_bytes() == original
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_migration_updates_repository_signing_configuration(
    dda: CliRunner, legacy_identity: Path, app: Application
) -> None:
    repository = legacy_identity / "repository"
    app.tools.git.capture(["init", str(repository)])
    with repository.as_cwd():
        app.tools.git.capture(["config", "user.signingkey", "${HOME}/.ssh/dda.pub"])

        result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

        result.check_exit_code(0)
        assert app.tools.git.capture(["config", "--local", "--get", "user.signingkey"]).strip() == "${HOME}/.ssh/dd.pub"


def test_ssh_doctor_migration_stops_before_renaming_for_invalid_git_configuration(
    dda: CliRunner, legacy_identity: Path
) -> None:
    (legacy_identity / ".gitconfig").write_text("[invalid", encoding="utf-8")
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(1)
    assert "bad config" in result.output
    assert _key_files(legacy_identity) == original_keys


@pytest.mark.parametrize("path_form", ["absolute", "home_variable", "key_variable", "ssh_home_token"])
def test_migration_expands_key_paths(temp_dir: Path, path_form: str) -> None:
    from dda.env.dev.ssh_migration import _renamed_path  # noqa: PLC2701

    ssh_dir = temp_dir / ".ssh"
    value = {
        "absolute": str(ssh_dir / "dda"),
        "home_variable": "${HOME}/.ssh/dda",
        "key_variable": "${DDA_LEGACY_KEY}",
        "ssh_home_token": "%d/.ssh/dda",
    }[path_form]
    expected = str(ssh_dir / "dd") if path_form == "key_variable" else value[:-3] + "dd"

    with EnvVars({"HOME": str(temp_dir), "DDA_LEGACY_KEY": str(ssh_dir / "dda")}):
        assert _renamed_path(value, ssh_dir) == expected


def test_ssh_doctor_migration_restores_private_key_when_public_rename_fails(
    dda: CliRunner, legacy_identity: Path, mocker: MockerFixture
) -> None:
    original_rename = Path.rename

    def fail_public_rename(self, target):
        if self.name == "dda.pub":
            msg = "Public selector rename failed."
            raise OSError(msg)
        return original_rename(self, target)

    mocker.patch.object(Path, "rename", fail_public_rename)
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(1)
    assert "Public selector rename failed" in result.output
    assert _key_files(legacy_identity) == original_keys


def test_ssh_doctor_migration_restores_git_and_keys_when_ssh_config_is_not_writable(
    dda: CliRunner, legacy_identity: Path, mocker: MockerFixture
) -> None:
    git_config = legacy_identity / ".gitconfig"
    original_git = b'[user]\n\tsigningKey = "~/.ssh/dda"\n'
    git_config.write_bytes(original_git)
    ssh_config = legacy_identity / ".ssh" / "config"
    original_ssh = b"Host github.com\n\tIdentityFile ~/.ssh/dda\n"
    ssh_config.write_bytes(original_ssh)
    original_write = Path.write_atomic

    def refuse_ssh_config(self, *args, **kwargs):
        if self == ssh_config:
            msg = "SSH configuration is not writable."
            raise PermissionError(msg)
        return original_write(self, *args, **kwargs)

    mocker.patch.object(Path, "write_atomic", refuse_ssh_config)
    original_keys = _key_files(legacy_identity)

    result = dda("--interactive", "env", "dev", "ssh", "doctor", input="y\n")

    result.check_exit_code(1)
    assert "SSH configuration is not writable" in result.output
    assert git_config.read_bytes() == original_git
    assert ssh_config.read_bytes() == original_ssh
    assert _key_files(legacy_identity) == original_keys
