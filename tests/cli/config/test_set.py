# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest


def test_value_string(dda, config_file, helpers):
    result = dda("config", "set", "foo", "bar")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        foo = "bar"
        """
    )

    assert config_file.data["foo"] == "bar"


def test_value_integer_positive(dda, config_file, helpers):
    result = dda("config", "set", "terminal.verbosity", "1")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [terminal]
        verbosity = 1
        """
    )

    assert config_file.model.terminal.verbosity == 1


def test_value_integer_negative(dda, config_file, helpers):
    result = dda("config", "set", "--", "terminal.verbosity", "-1")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [terminal]
        verbosity = -1
        """
    )

    assert config_file.model.terminal.verbosity == -1


@pytest.mark.parametrize("value", [True, False])
def test_value_boolean(dda, config_file, helpers, value):
    toml_value = str(value).lower()
    result = dda("config", "set", "env.dev.universal-shell", toml_value)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        [env.dev]
        universal-shell = {toml_value}
        """
    )

    assert config_file.model.env.dev.universal_shell is value


def test_value_deep(dda, config_file, helpers):
    result = dda("config", "set", "github.auth.user", "foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [github.auth]
        user = "foo"
        """
    )

    assert config_file.model.github.auth.user == "foo"


def test_value_complex_sequence(dda, config_file, helpers):
    result = dda("config", "set", "a.b", "['/foo', '/bar']")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [a]
        b = ["/foo", "/bar"]
        """
    )

    assert config_file.data["a"]["b"] == ["/foo", "/bar"]


def test_value_complex_map(dda, config_file, helpers):
    result = dda("config", "set", "z", "{'a': '/foo', 'b': '/bar'}")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [z]
        a = "/foo"
        b = "/bar"
        """
    )

    assert config_file.data["z"] == {"a": "/foo", "b": "/bar"}


def test_value_hidden(dda, config_file, helpers):
    result = dda("config", "set", "github.auth.token", "foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [github.auth]
        token = "*****"
        """
    )

    assert config_file.model.github.auth.token == "foo"


def test_prompt(dda, config_file, helpers):
    result = dda("config", "set", "github.auth.user", input="foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Value: foo
        [github.auth]
        user = "foo"
        """
    )

    assert config_file.model.github.auth.user == "foo"


def test_prompt_hidden(dda, config_file, helpers):
    result = dda("config", "set", "github.auth.token", input="foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Value:{" "}
        [github.auth]
        token = "*****"
        """
    )

    assert config_file.model.github.auth.token == "foo"


def test_prevent_invalid_config(dda, config_file, helpers):
    original_verbosity = config_file.model.terminal.verbosity
    result = dda("config", "set", "terminal.verbosity", "foo")

    assert result.exit_code == 1
    assert result.output == helpers.dedent(
        """
        Expected `int`, got `str` - at `$.terminal.verbosity`
        """
    )

    assert config_file.model.terminal.verbosity == original_verbosity
