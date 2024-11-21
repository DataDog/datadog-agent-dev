# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import importlib
import sys
import time
from functools import cached_property, partial
from typing import TYPE_CHECKING, Any

import rich_click as click

if TYPE_CHECKING:
    from deva.cli.application import Application


class DynamicContext(click.RichContext):
    @cached_property
    def dynamic_params(self) -> list[click.Option]:
        # https://github.com/pallets/click/pull/2784
        return []

    def get_dynamic_sibling(self) -> click.RichContext:
        cmd = DynamicCommand(name=None, params=self.dynamic_params)
        return cmd.make_context(info_name=None, args=self.args, parent=self)
    
    def exit(self, code: int = 0) -> None:
        self.obj.send_telemetry(code)
        super().exit(code)

    def fail(self, message: str) -> None:
        self.obj.send_telemetry(1)
        super().fail(message)

    

class DynamicCommand(click.RichCommand):
    context_class = DynamicContext

    def __init__(self, *args: Any, dependencies: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

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
        if self.callback is not None and self._dependencies is not None:
            from dep_sync import Dependency, dependency_state

            dep_state = dependency_state(list(map(Dependency, self._dependencies)))
            if dep_state.missing:
                import shutil

                if uv_exe := shutil.which("uv"):
                    command = [uv_exe, "pip", "install", "--python", sys.executable]
                else:
                    command = [sys.executable, "-m", "pip", "install"]

                command.extend(map(str, dep_state.missing))

                app.display_waiting("Synchronizing dependencies...")
                app.subprocess.run(command)
        res = super().invoke(ctx)
        app.send_telemetry(0)
    
        return res


class DynamicGroup(click.RichGroup):
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
