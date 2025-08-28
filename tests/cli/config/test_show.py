# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.env.dev import DEFAULT_DEV_ENV


def test_default_scrubbed(dda, config_file, helpers, default_cache_dir, default_data_dir):
    config_file.data["github"]["auth"] = {"user": "foo", "token": "bar"}
    config_file.save()

    result = dda("config", "show")

    default_cache_directory = str(default_cache_dir).replace("\\", "\\\\")
    default_data_directory = str(default_data_dir).replace("\\", "\\\\")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        [orgs.default]

        [env.dev]
        default-type = "{DEFAULT_DEV_ENV}"
        clone-repos = false
        universal-shell = false
        editor = "vscode"

        [tools.bazel]
        managed = "auto"

        [tools.git]
        username = "Foo Bar"
        user_email = "foo@bar.baz"

        [storage]
        data = "{default_data_directory}"
        cache = "{default_cache_directory}"

        [github.auth]
        user = "foo"
        token = "*****"

        [terminal]
        verbosity = 0

        [terminal.styles]
        error = "bold red"
        warning = "bold yellow"
        info = "bold"
        success = "bold cyan"
        waiting = "bold magenta"
        debug = "bold on bright_black"
        spinner = "simpleDotsScrolling"

        [update]
        mode = "check"

        [update.check]
        period = "2w"
        """
    )


def test_reveal(dda, config_file, helpers, default_cache_dir, default_data_dir):
    config_file.data["github"]["auth"] = {"user": "foo", "token": "bar"}
    config_file.save()

    result = dda("config", "show", "-a")

    default_cache_directory = str(default_cache_dir).replace("\\", "\\\\")
    default_data_directory = str(default_data_dir).replace("\\", "\\\\")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        [orgs.default]

        [env.dev]
        default-type = "{DEFAULT_DEV_ENV}"
        clone-repos = false
        universal-shell = false
        editor = "vscode"

        [tools.bazel]
        managed = "auto"

        [tools.git]
        username = "Foo Bar"
        user_email = "foo@bar.baz"

        [storage]
        data = "{default_data_directory}"
        cache = "{default_cache_directory}"

        [github.auth]
        user = "foo"
        token = "bar"

        [terminal]
        verbosity = 0

        [terminal.styles]
        error = "bold red"
        warning = "bold yellow"
        info = "bold"
        success = "bold cyan"
        waiting = "bold magenta"
        debug = "bold on bright_black"
        spinner = "simpleDotsScrolling"

        [update]
        mode = "check"

        [update.check]
        period = "2w"
        """
    )
