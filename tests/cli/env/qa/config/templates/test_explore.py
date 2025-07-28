# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.usefixtures("private_storage")]


def test_root_no_templates(dda, temp_dir, mocker):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    assert not templates_dir.exists()

    mock = mocker.patch("click.launch")
    result = dda("env", "qa", "config", "templates", "explore")
    result.check(exit_code=0)

    mock.assert_called_once_with(str(templates_dir / "default"), locate=True)
    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["default"]


def test_root_existing_default(dda, temp_dir, mocker):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "default"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").touch()

    mock = mocker.patch("click.launch")
    result = dda("env", "qa", "config", "templates", "explore")
    result.check(exit_code=0)

    mock.assert_called_once_with(str(template_dir), locate=True)
    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["default"]


def test_root_existing_non_default(dda, temp_dir, mocker):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "foo"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").touch()

    mock = mocker.patch("click.launch")
    result = dda("env", "qa", "config", "templates", "explore")
    result.check(exit_code=0)

    mock.assert_called_once_with(str(template_dir), locate=True)
    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["foo"]


def test_selection(dda, temp_dir, mocker):
    mock = mocker.patch("click.launch")
    template_dir = temp_dir / "data" / "env" / "config" / "templates" / "foo"
    template_dir.ensure_dir()
    config_file = template_dir / "datadog.yaml"
    config_file.touch()

    result = dda("env", "qa", "config", "templates", "explore", "foo")
    result.check(exit_code=0)
    mock.assert_called_once_with(str(config_file), locate=True)


def test_selection_not_found(dda, helpers, mocker):
    mock = mocker.patch("click.launch")
    result = dda("env", "qa", "config", "templates", "explore", "foo")
    result.check(
        exit_code=1,
        output=helpers.dedent(
            """
            Template not found: foo
            """
        ),
    )
    mock.assert_not_called()
