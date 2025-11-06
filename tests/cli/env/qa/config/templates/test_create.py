# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.usefixtures("private_storage")]


def test_create_new(dda, helpers, temp_dir):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    assert not templates_dir.exists()

    result = dda("env", "qa", "config", "templates", "create", "foo")
    result.check(
        exit_code=0,
        stdout=helpers.dedent(
            """
            Template created: foo
            """
        ),
    )
    assert (templates_dir / "foo" / "datadog.yaml").is_file()


def test_create_existing(dda, helpers, temp_dir):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "foo"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").touch()

    result = dda("env", "qa", "config", "templates", "create", "foo")
    result.check(
        exit_code=1,
        output=helpers.dedent(
            """
            Template already exists: foo
            """
        ),
    )
