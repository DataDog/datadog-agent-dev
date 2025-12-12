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
            {"n_packages": 2},
            {"n_packages": 1, "build_tags": {"debug"}},
            {"n_packages": 0, "build_tags": {"prod"}, "gcflags": ["all=-N -l"], "ldflags": ["all=-s -w", "-dumpdep"]},
            {"n_packages": 2, "build_tags": {"prod"}, "gcflags": ["all=-N -l"], "ldflags": ["all=-s -w", "-dumpdep"]},
            {"n_packages": 0, "force_rebuild": True},
        ],
    )
    def test_command_formation(self, app, mocker, call_args, get_random_filename):
        # Patch the raw _build method to avoid running anything
        mocker.patch("dda.tools.go.Go._build", return_value="output")

        # Generate dummy package and output paths
        n_packages = call_args.pop("n_packages", 0)
        packages: tuple[Path, ...] = tuple(get_random_filename() for _ in range(n_packages))
        output: Path = get_random_filename()
        app.tools.go.build(
            *packages,
            output=output,
            **call_args,
        )

        flags = {
            ("-trimpath",),
            ("-mod=readonly",),
            (f"-o={output}",),
            # ("-v",), # By default verbosity is INFO
            # ("-x",),
        }

        if not (platform.system() == "Windows" and platform.machine() == "arm64"):
            flags.add(("-race",))

        if call_args.get("build_tags"):
            flags.add(("-tags", ",".join(sorted(call_args.get("build_tags", [])))))
        if call_args.get("gcflags"):
            flags.add((f"-gcflags={' '.join(call_args.get('gcflags'))}",))
        if call_args.get("ldflags"):
            flags.add((f"-ldflags={' '.join(call_args.get('ldflags'))}",))
        if call_args.get("force_rebuild"):
            flags.add(("-a",))

        seen_command_parts = app.tools.go._build.call_args[0][0]  # noqa: SLF001

        flags_len = len(flags)
        seen_flags: list[str] = seen_command_parts[: flags_len + 1]
        for flag_tuple in flags:
            assert flag_tuple[0] in seen_flags

            if len(flag_tuple) > 1:
                flag_index = seen_flags.index(flag_tuple[0])
                assert seen_flags[flag_index + 1] == flag_tuple[1]

        if n_packages > 0:
            assert seen_command_parts[-len(packages) :] == [str(package) for package in packages]

    # This test is quite slow, we'll only run it in CI
    @pytest.mark.requires_ci
    @pytest.mark.skip_macos  # Go binary is not installed on macOS CI runners
    def test_build_project(self, app, temp_dir):
        for tag, output_mark in [("prod", "PRODUCTION"), ("debug", "DEBUG")]:
            with (Path(__file__).parent / "fixtures" / "small_go_project").as_cwd():
                app.tools.go.build(
                    ".",
                    output=(temp_dir / "testbinary").absolute(),
                    build_tags={tag},
                    force_rebuild=True,
                )

                assert (temp_dir / "testbinary").is_file()
                output = app.subprocess.capture(str(temp_dir / "testbinary"))
                assert output_mark in output
                # Note: doing both builds in the same test with the same name also allows us to test the force rebuild
