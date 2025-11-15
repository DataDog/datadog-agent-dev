# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import platform

import pytest

from dda.utils.fs import Path


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


class TestBuild:
    @pytest.mark.parametrize(
        "call_args",
        [
            {},
            {"build_tags": ["debug"]},
            {"build_tags": ["prod"], "gcflags": "-gcflags=all=-N -l", "ldflags": "-ldflags=all=-s -w"},
            {
                "build_tags": ["prod"],
                "gcflags": "-gcflags=all=-N -l",
                "ldflags": "-ldflags=all=-s -w",
                "go_mod": "../go.mod",
            },
            {"force_rebuild": True},
        ],
    )
    def test_command_formation(self, app, mocker, call_args, get_random_filename):
        # Patch the raw _build method to avoid running anything
        mocker.patch("dda.tools.go.Go._build", return_value="output")

        # Generate dummy entrypoint and output paths
        entrypoint: Path = get_random_filename()
        output: Path = get_random_filename()
        app.tools.go.build(
            entrypoint=entrypoint,
            output=output,
            **call_args,
        )

        # Assert the command is formed correctly
        expected_command_flags = {
            "-trimpath",
            f"-o={output}",
            # "-v", # By default verbosity is INFO
            # "-x",
        }
        if not (platform.machine() == "windows" and platform.machine() == "arm64"):
            expected_command_flags.add("-race")

        if call_args.get("build_tags"):
            expected_command_flags.add(f"-tags={' '.join(sorted(call_args.get('build_tags', [])))}")
        if call_args.get("gcflags"):
            expected_command_flags.add(f"-gcflags={call_args.get('gcflags')}")
        if call_args.get("ldflags"):
            expected_command_flags.add(f"-ldflags={call_args.get('ldflags')}")
        if call_args.get("go_mod"):
            expected_command_flags.add(f"-mod={call_args.get('go_mod')}")
        if call_args.get("force_rebuild"):
            expected_command_flags.add("-a")

        seen_command = app.tools.go._build.call_args[0][0]  # noqa: SLF001
        seen_command_flags = {x for x in seen_command if x.startswith("-")}
        assert seen_command_flags == expected_command_flags
        assert seen_command[len(seen_command_flags)] == str(entrypoint)

    # This tests is quite slow, we'll only run it in CI
    @pytest.mark.requires_ci
    @pytest.mark.skip_macos  # Go binary is not installed on macOS CI runners
    def test_build_project(self, app, temp_dir):
        for tag, output_mark in [("prod", "PRODUCTION"), ("debug", "DEBUG")]:
            with (Path(__file__).parent / "fixtures" / "small_go_project").as_cwd():
                app.tools.go.build(
                    entrypoint=".",
                    output=(temp_dir / "testbinary").absolute(),
                    build_tags=[tag],
                )

                assert (temp_dir / "testbinary").is_file()
                output = app.subprocess.capture(str(temp_dir / "testbinary"))
                assert output_mark in output
                # Note: doing both builds in the same test with the same name also allows us to test the force rebuild
