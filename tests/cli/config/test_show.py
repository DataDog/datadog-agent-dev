# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.env.dev import DEFAULT_DEV_ENV


def test_default_scrubbed(
    dda, config_file, helpers, default_cache_dir, default_data_dir, default_git_author, default_gopath, default_gocache
):
    config_file.data["github"]["auth"] = {"user": "foo", "token": "bar"}
    config_file.data["tools"]["go"]["gopath"] = str(default_gopath)
    config_file.data["tools"]["go"]["gocache"] = str(default_gocache)
    config_file.save()

    result = dda("config", "show")

    default_cache_directory = str(default_cache_dir).replace("\\", "\\\\")
    default_data_directory = str(default_data_dir).replace("\\", "\\\\")
    default_gopath = str(default_gopath).replace("\\", "\\\\")
    default_gocache = str(default_gocache).replace("\\", "\\\\")

    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            [orgs.default]

            [env.dev]
            default-type = "{DEFAULT_DEV_ENV}"
            clone-repos = false
            universal-shell = false
            editor = "vscode"

            [tools.bazel]
            managed = "auto"

            [tools.git.author]
            name = "{default_git_author.name}"
            email = "{default_git_author.email}"

            [tools.go]
            gopath = "{default_gopath}"
            gocache = "{default_gocache}"

            [storage]
            data = "{default_data_directory}"
            cache = "{default_cache_directory}"

            [github.auth]
            user = "foo"
            token = "*****"

            [user]
            name = "auto"
            email = "auto"

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

            [telemetry]
            anon = true
            """
        ),
    )


def test_reveal(
    dda, config_file, helpers, default_cache_dir, default_data_dir, default_git_author, default_gopath, default_gocache
):
    config_file.data["github"]["auth"] = {"user": "foo", "token": "bar"}
    config_file.data["tools"]["go"]["gopath"] = str(default_gopath)
    config_file.data["tools"]["go"]["gocache"] = str(default_gocache)
    config_file.save()

    result = dda("config", "show", "-a")

    default_cache_directory = str(default_cache_dir).replace("\\", "\\\\")
    default_data_directory = str(default_data_dir).replace("\\", "\\\\")
    default_gopath = str(default_gopath).replace("\\", "\\\\")
    default_gocache = str(default_gocache).replace("\\", "\\\\")

    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            [orgs.default]

            [env.dev]
            default-type = "{DEFAULT_DEV_ENV}"
            clone-repos = false
            universal-shell = false
            editor = "vscode"

            [tools.bazel]
            managed = "auto"

            [tools.git.author]
            name = "{default_git_author.name}"
            email = "{default_git_author.email}"

            [tools.go]
            gopath = "{default_gopath}"
            gocache = "{default_gocache}"

            [storage]
            data = "{default_data_directory}"
            cache = "{default_cache_directory}"

            [github.auth]
            user = "foo"
            token = "bar"

            [user]
            name = "auto"
            email = "auto"

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

            [telemetry]
            anon = true
            """
        ),
    )
