# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.usefixtures("private_storage")]


def test_root_no_templates(dda, helpers, temp_dir):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    assert not templates_dir.exists()

    result = dda("env", "qa", "config", "templates", "find")
    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            {temp_dir / "data" / "env" / "config" / "templates"}
            """
        ),
    )
    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["default"]


def test_root_existing_non_default(dda, helpers, temp_dir):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "foo"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").touch()

    result = dda("env", "qa", "config", "templates", "find")
    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            {temp_dir / "data" / "env" / "config" / "templates"}
            """
        ),
    )
    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["foo"]


def test_selection(dda, helpers, temp_dir):
    template_dir = temp_dir / "data" / "env" / "config" / "templates" / "foo"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").touch()

    result = dda("env", "qa", "config", "templates", "find", "foo")
    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            f"""
            {template_dir}
            """
        ),
    )


def test_selection_not_found(dda, helpers):
    result = dda("env", "qa", "config", "templates", "find", "foo")
    result.check(
        exit_code=1,
        output=helpers.dedent(
            """
            Template not found: foo
            """
        ),
    )
