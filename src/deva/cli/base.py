# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import importlib
import sys
from functools import cached_property, partial
from time import perf_counter_ns
from typing import TYPE_CHECKING, Any

import rich_click as click
from click.exceptions import Exit, UsageError

if TYPE_CHECKING:
    from types import TracebackType

    from deva.cli.application import Application


class DynamicContext(click.RichContext):
    @cached_property
    def dynamic_params(self) -> list[click.Option]:
        # https://github.com/pallets/click/pull/2784
        return []

    def get_dynamic_sibling(self) -> click.RichContext:
        cmd = DynamicCommand(name=None, params=self.dynamic_params)
        return cmd.make_context(info_name=None, args=self.args, parent=self)

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, tb: TracebackType | None
    ) -> None:
        if self._depth == 1:
            app: Application = self.obj

            # https://github.com/pallets/click/blob/8.1.8/src/click/exceptions.py#L296
            if isinstance(exc_value, Exit):
                exit_code = exc_value.exit_code
            # https://github.com/pallets/click/blob/8.1.8/src/click/exceptions.py#L64
            elif isinstance(exc_value, UsageError):
                exit_code = 2
            # https://github.com/pallets/click/blob/8.1.8/src/click/exceptions.py#L29
            else:
                exit_code = 1

            app.telemetry.submit_data("exit_code", str(exit_code))
            app.telemetry.submit_data("end_time", str(perf_counter_ns()))

        super().__exit__(exc_type, exc_value, tb)


class DynamicCommand(click.RichCommand):
    context_class = DynamicContext

    def __init__(
        self,
        *args: Any,
        features: list[str] | None = None,
        dependencies: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self._features = features
        self._dependencies = dependencies

    def get_params(self, ctx: click.Context) -> list[click.Parameter]:
        # https://github.com/pallets/click/pull/2784
        # https://github.com/pallets/click/blob/8.1.7/src/click/core.py#L1255
        params = [*self.params, *ctx.dynamic_params]  # type: ignore[attr-defined]
        if (help_option := self.get_help_option(ctx)) is not None:
            params.append(help_option)

        return params

    def invoke(self, ctx: click.Context) -> Any:
        app: Application = ctx.obj
        if self.callback is not None and app.dynamic_deps_allowed:
            if self._features is not None:
                ensure_features_installed(self._features, app=app)

            if self._dependencies is not None:
                ensure_deps_installed(self._dependencies, app=app)

        return super().invoke(ctx)


class DynamicGroup(click.RichGroup):
    context_class = DynamicContext
    command_class = DynamicCommand

    def __init__(
        self, *args: Any, external_plugins: bool | None = None, subcommands: tuple[str], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)

        self._external_plugins = external_plugins
        # e.g. ('dev', 'runtime', 'qa')
        self._subcommands = subcommands

    @property
    def _module(self) -> str:
        # e.g. deva.cli.env
        return self.callback.__module__

    @cached_property
    def _plugins(self) -> dict[str, str]:
        import os

        import find_exe

        plugin_prefix = self.callback.__module__.replace("deva.cli", "deva", 1).replace(".", "-")
        plugin_prefix = f"{plugin_prefix}-"
        exe_pattern = f"^{plugin_prefix}[^-]+$"

        plugins: dict[str, str] = {}
        for executable in find_exe.with_pattern(exe_pattern):
            exe_name = os.path.splitext(os.path.basename(executable))[0]
            plugin_name = exe_name[len(plugin_prefix) :]
            plugins[plugin_name] = executable

        return plugins

    @classmethod
    def _create_module_meta_key(cls, module: str) -> str:
        return f"{module}.plugins"

    def _external_plugins_allowed(self, ctx: click.Context) -> bool:
        if self._external_plugins is not None:
            return self._external_plugins

        parent_module_parts = self._module.split(".")[:-1]
        parent_key = self._create_module_meta_key(".".join(parent_module_parts))
        return bool(ctx.meta[parent_key])

    def list_commands(self, ctx: click.Context) -> list[str]:
        commands = super().list_commands(ctx)
        commands.extend(self._subcommands)
        if self._external_plugins_allowed(ctx):
            commands.extend(self._plugins)
        return sorted(commands)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        # Pass down the default setting for allowing external plugins, see:
        # https://click.palletsprojects.com/en/8.1.x/api/#click.Context.meta
        ctx.meta[self._create_module_meta_key(self._module)] = self._external_plugins_allowed(ctx)

        if cmd_name in self._subcommands:
            return self._lazy_load(cmd_name)

        if cmd_name in self._plugins:
            return _get_external_plugin_callback(cmd_name, self._plugins[cmd_name])

        return super().get_command(ctx, cmd_name)

    def _lazy_load(self, cmd_name: str) -> click.Command:
        import_path = f"{self._module}.{cmd_name}"
        mod = importlib.import_module(import_path)
        cmd_object = getattr(mod, "cmd", None)
        if not isinstance(cmd_object, click.Command):
            message = f"Unable to lazily load command: {import_path}.cmd"
            raise TypeError(message)

        return cmd_object


def ensure_deps_installed(
    dependencies: list[str],
    *,
    app: Application,
    constraints: list[str] | None = None,
    sys_path: list[str] | None = None,
) -> None:
    if not dependencies:
        return

    from dep_sync import Dependency, dependency_state

    from deva.utils.fs import temp_directory

    dep_state = dependency_state(list(map(Dependency, dependencies)), sys_path=sys_path)
    if dep_state.missing:
        command = ["pip", "install"]
        app.display_waiting("Synchronizing dependencies")
        with temp_directory() as temp_dir:
            requirements_file = temp_dir / "requirements.txt"
            requirements_file.write_text("\n".join(map(str, dep_state.missing)))
            command.extend(["-r", str(requirements_file)])
            if constraints:
                constraints_file = temp_dir / "constraints.txt"
                constraints_file.write_text("\n".join(constraints))
                command.extend(["-c", str(constraints_file)])

            app.tools.uv.run(command)


def ensure_features_installed(
    features: list[str],
    *,
    app: Application,
    prefix: str = sys.prefix,
) -> None:
    if not features:
        return

    import shutil
    import sysconfig

    from deva.utils.fs import Path, temp_directory
    from deva.utils.process import EnvVars

    # https://docs.astral.sh/uv/reference/cli/#uv-sync
    command = [
        "sync",
        "--frozen",
        # Prevent synchronizing the project itself because some required dependencies
        # have extension modules. On Windows, files cannot be modified while they are
        # in use. This also affects the entry point script `deva.exe`.
        "--no-install-project",
        "--inexact",
    ]
    for feature in features:
        command.extend(["--only-group", feature])

    with temp_directory() as temp_dir:
        data_dir = Path(sysconfig.get_path("data")) / "deva-data"
        for filename in ("uv.lock", "pyproject.toml"):
            data_file = data_dir / filename
            shutil.copy(data_file, temp_dir)

        env_vars = EnvVars()
        # https://docs.astral.sh/uv/concepts/projects/config/#project-environment-path
        env_vars["UV_PROJECT_ENVIRONMENT"] = prefix
        # Remove warning from output if we happen to display it due to an error
        env_vars.pop("VIRTUAL_ENV", None)

        app.tools.uv.wait(command, message="Synchronizing dependencies", cwd=str(temp_dir), env=env_vars)


def _get_external_plugin_callback(cmd_name: str, executable: str) -> click.Command:
    @click.command(
        name=cmd_name,
        short_help="[external plugin]",
        context_settings={"help_option_names": [], "ignore_unknown_options": True},
    )
    @click.argument("args", required=True, nargs=-1)
    @click.pass_context
    def _external_plugin_callback(ctx: click.Context, args: tuple[str, ...]) -> None:
        import subprocess

        process = subprocess.run([executable, *args], check=False)
        ctx.exit(process.returncode)

    return _external_plugin_callback


dynamic_command = partial(click.command, cls=DynamicCommand)
dynamic_group = partial(click.group, cls=DynamicGroup)
