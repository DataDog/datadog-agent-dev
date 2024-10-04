# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest


def test_value_string(deva, config_file, helpers):
    result = deva("config", "set", "foo", "bar")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        foo = "bar"
        """
    )

    assert config_file.data["foo"] == "bar"


def test_value_integer_positive(deva, config_file, helpers):
    result = deva("config", "set", "terminal.verbosity", "1")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [terminal]
        verbosity = 1
        """
    )

    assert config_file.model.terminal.verbosity == 1


def test_value_integer_negative(deva, config_file, helpers):
    result = deva("config", "set", "--", "terminal.verbosity", "-1")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [terminal]
        verbosity = -1
        """
    )

    assert config_file.model.terminal.verbosity == -1


@pytest.mark.parametrize("value", [True, False])
def test_value_boolean(deva, config_file, helpers, value):
    toml_value = str(value).lower()
    result = deva("config", "set", "foo", toml_value)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        foo = {toml_value}
        """
    )

    assert config_file.data["foo"] is value


def test_value_deep(deva, config_file, helpers):
    result = deva("config", "set", "github.auth.user", "foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [github.auth]
        user = "foo"
        """
    )

    assert config_file.model.github.auth.user == "foo"


def test_value_complex_sequence(deva, config_file, helpers):
    result = deva("config", "set", "a.b", "['/foo', '/bar']")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [a]
        b = ["/foo", "/bar"]
        """
    )

    assert config_file.data["a"]["b"] == ["/foo", "/bar"]


def test_value_complex_map(deva, config_file, helpers):
    result = deva("config", "set", "z", "{'a': '/foo', 'b': '/bar'}")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [z]
        a = "/foo"
        b = "/bar"
        """
    )

    assert config_file.data["z"] == {"a": "/foo", "b": "/bar"}


def test_value_hidden(deva, config_file, helpers):
    result = deva("config", "set", "github.auth.token", "foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        [github.auth]
        token = "*****"
        """
    )

    assert config_file.model.github.auth.token == "foo"


def test_prompt(deva, config_file, helpers):
    result = deva("config", "set", "github.auth.user", input="foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Value: foo
        [github.auth]
        user = "foo"
        """
    )

    assert config_file.model.github.auth.user == "foo"


def test_prompt_hidden(deva, config_file, helpers):
    result = deva("config", "set", "github.auth.token", input="foo")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Value:{" "}
        [github.auth]
        token = "*****"
        """
    )

    assert config_file.model.github.auth.token == "foo"


def test_prevent_invalid_config(deva, config_file, helpers):
    original_verbosity = config_file.model.terminal.verbosity
    result = deva("config", "set", "terminal.verbosity", "foo")

    assert result.exit_code == 1
    assert result.output == helpers.dedent(
        """
        Expected `int`, got `str` - at `$.terminal.verbosity`
        """
    )

    assert config_file.model.terminal.verbosity == original_verbosity
