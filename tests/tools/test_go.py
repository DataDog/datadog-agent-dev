# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations


def test_default(app):
    with app.tools.go.execution_context([]) as context:
        assert context.env_vars == {}


class TestPrecedence:
    def test_workspace_file(self, app, temp_dir):
        (temp_dir / "go.work").write_text("stuff\ngo X.Y.Z\nstuff")
        with temp_dir.as_cwd(), app.tools.go.execution_context([]) as context:
            assert context.env_vars == {"GOTOOLCHAIN": "goX.Y.Z"}

    def test_module_file(self, app, temp_dir):
        (temp_dir / "go.work").write_text("stuff\ngo X.Y.Z\nstuff")
        (temp_dir / "go.mod").write_text("stuff\ngo X.Y.Zrc1\nstuff")
        with temp_dir.as_cwd(), app.tools.go.execution_context([]) as context:
            assert context.env_vars == {"GOTOOLCHAIN": "goX.Y.Zrc1"}

    def test_version_file(self, app, temp_dir):
        (temp_dir / "go.work").write_text("stuff\ngo X.Y.Z\nstuff")
        (temp_dir / "go.mod").write_text("stuff\ngo X.Y.Zrc1\nstuff")
        (temp_dir / ".go-version").write_text("X.Y.Zrc2")
        with temp_dir.as_cwd(), app.tools.go.execution_context([]) as context:
            assert context.env_vars == {"GOTOOLCHAIN": "goX.Y.Zrc2"}
