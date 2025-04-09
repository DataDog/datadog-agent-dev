# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from functools import cached_property, partial
from importlib.util import module_from_spec, spec_from_file_location
from time import perf_counter_ns
from typing import TYPE_CHECKING, Any

import rich_click as click
from click.exceptions import Exit, UsageError
from rich_click.rich_help_formatter import RichHelpFormatter

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from dda.cli.application import Application


def _building_docs() -> bool:
    return os.environ.get("DDA_BUILDING_DOCS") == "true"


class DocumentingHelpFormatter(RichHelpFormatter):
    def getvalue(self) -> str:
        # https://github.com/ewels/rich-click/pull/230
        if self.console.record:
            return self.console.export_text()

        return super().getvalue()


class DynamicContext(click.RichContext):
    formatter_class = DocumentingHelpFormatter
    export_console_as = "html" if _building_docs() else None

    @cached_property
    def allow_external_plugins(self) -> bool:
        command: DynamicGroup = self.command  # type: ignore[assignment]
        if command.allow_external_plugins is not None:
            return command.allow_external_plugins

        parent: DynamicContext | None = self.parent  # type: ignore[assignment]
        if parent is None:
            return bool(command.allow_external_plugins)

        return parent.allow_external_plugins

    @cached_property
    def external_plugins(self) -> dict[str, str]:
        import os

        import find_exe

        plugin_prefix = f"{self.command_path.replace(' ', '-')}-"
        exe_pattern = f"^{plugin_prefix}[^-]+$"

        plugins: dict[str, str] = {}
        for executable in find_exe.with_pattern(exe_pattern):
            exe_name = os.path.splitext(os.path.basename(executable))[0]
            plugin_name = exe_name[len(plugin_prefix) :]
            plugins[plugin_name] = executable

        return plugins

    @cached_property
    def search_paths(self) -> dict[int, str]:
        parent: DynamicContext | None = self.parent  # type: ignore[assignment]
        if parent is None:
            command: DynamicGroup = self.command  # type: ignore[assignment]
            return command.get_default_search_paths()

        new_search_paths = {}
        parent_cmd_name = self.command_path.split()[-1]
        for i, search_path in parent.search_paths.items():
            group_dir = os.path.join(search_path, parent_cmd_name)
            cmd_path = os.path.join(group_dir, "__init__.py")
            if os.path.isfile(cmd_path):
                new_search_paths[i] = group_dir

        return new_search_paths

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
        app: Application | None = self.obj
        if app is not None and self._depth == 1:
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
        self.__help_option: click.Option | None = None

        self.__dynamic_path_id = 0

    def set_dynamic_path_id(self, dynamic_path_id: int) -> None:
        self.__dynamic_path_id = dynamic_path_id

    @property
    def dynamic_path_id(self) -> int:
        return self.__dynamic_path_id

    def get_params(self, ctx: DynamicContext) -> list[click.Parameter]:  # type: ignore[override]
        # https://github.com/pallets/click/pull/2784
        # https://github.com/pallets/click/blob/8.1.7/src/click/core.py#L1255
        params = [*self.params, *ctx.dynamic_params]
        if (help_option := self.get_help_option(ctx)) is not None:
            params.append(help_option)

        return params

    def invoke(self, ctx: DynamicContext) -> Any:  # type: ignore[override]
        app: Application = ctx.obj
        if self.callback is not None and app.dynamic_deps_allowed:
            if self._features is not None:
                ensure_features_installed(self._features, app=app)

            if self._dependencies is not None:
                ensure_deps_installed(self._dependencies, app=app)

        # Only add dynamic command paths to Python's search path, the first one is always the root command group
        if self.dynamic_path_id != 0:
            root_ctx = ctx
            while root_ctx.parent is not None:
                parent: DynamicContext = root_ctx.parent  # type: ignore[assignment]
                root_ctx = parent

            search_path = root_ctx.search_paths[self.dynamic_path_id]
            sys.path.insert(0, search_path)

        try:
            return super().invoke(ctx)
        finally:
            if self.dynamic_path_id != 0:
                sys.path.pop(0)

    def get_help_option(self, ctx: DynamicContext) -> click.Option | None:  # type: ignore[override]
        if self.__help_option is not None:
            return self.__help_option

        help_option = super().get_help_option(ctx)
        if help_option is not None:
            original_callback = help_option.callback

            all_callbacks_executed = False

            def callback(ctx: DynamicContext, param: click.Parameter, value: Any) -> None:
                nonlocal all_callbacks_executed
                if not all_callbacks_executed:
                    # Callbacks for other parameters may influence the help text
                    for other_param in ctx.command.get_params(ctx):
                        if other_param is not param and other_param.callback is not None:
                            other_param.callback(ctx, other_param, None)
                    all_callbacks_executed = True

                if original_callback is not None:
                    original_callback(ctx, param, value)

            help_option.callback = callback  # type: ignore[assignment]
            self.__help_option = help_option

        return self.__help_option


class DynamicGroup(click.RichGroup):
    context_class = DynamicContext
    command_class = DynamicCommand

    def __init__(
        self,
        *args: Any,
        allow_external_plugins: bool | None = None,
        subcommand_filter: Callable[[str], bool] | None = None,
        search_path_finder: Callable[[], list[str]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.allow_external_plugins = allow_external_plugins
        self.__subcommand_filter = subcommand_filter
        self.__search_path_finder = search_path_finder
        self.__subcommand_cache: list[str] | None = None

        self.__dynamic_path_id = 0

    def set_dynamic_path_id(self, dynamic_path_id: int) -> None:
        self.__dynamic_path_id = dynamic_path_id

    @property
    def dynamic_path_id(self) -> int:
        return self.__dynamic_path_id

    def list_commands(self, ctx: DynamicContext) -> list[str]:  # type: ignore[override]
        if self.__subcommand_cache is not None:
            return self.__subcommand_cache

        commands = super().list_commands(ctx)
        commands.extend(
            entry
            for search_path in ctx.search_paths.values()
            for entry in os.listdir(search_path)
            if not entry.startswith(("_", ".")) and os.path.isfile(os.path.join(search_path, entry, "__init__.py"))
        )

        if not _building_docs() and ctx.allow_external_plugins:
            commands.extend(ctx.external_plugins)

        self.__subcommand_cache = sorted(command for command in commands if self._subcommand_allowed(command))
        return self.__subcommand_cache

    def get_command(self, ctx: DynamicContext, cmd_name: str) -> DynamicCommand | DynamicGroup | None:  # type: ignore[override]
        command: DynamicCommand | DynamicGroup | None = super().get_command(ctx, cmd_name)  # type: ignore[assignment]
        if command is not None or not self._subcommand_allowed(cmd_name):
            return command

        for i, search_path in ctx.search_paths.items():
            cmd_path = os.path.join(search_path, cmd_name, "__init__.py")
            if os.path.isfile(cmd_path):
                command = self._lazy_load(cmd_name, cmd_path)
                command.name = cmd_name
                command.set_dynamic_path_id(i)
                return command

        if not _building_docs() and cmd_name in ctx.external_plugins:
            return _get_external_plugin_callback(cmd_name, ctx.external_plugins[cmd_name])

        return command

    def _subcommand_allowed(self, cmd_name: str) -> bool:
        return self.__subcommand_filter is None or self.__subcommand_filter(cmd_name)

    def get_default_search_paths(self) -> dict[int, str]:
        callback = self.callback
        # functools.partial
        while callback is not None and hasattr(callback, "__wrapped__"):
            callback = callback.__wrapped__

        search_paths = [os.getcwd() if callback is None else os.path.dirname(callback.__code__.co_filename)]
        if not _building_docs() and self.__search_path_finder is not None:
            search_paths.extend(self.__search_path_finder())

        return dict(enumerate(search_paths))

    @classmethod
    def _lazy_load(cls, cmd_name: str, path: str) -> DynamicCommand | DynamicGroup:
        spec = spec_from_file_location(cmd_name, path)
        if spec is None:
            message = f"Path to command `{cmd_name}` doesn't exist: {path}"
            raise ValueError(message)

        module = module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        cmd_object = getattr(module, "cmd", None)
        if not isinstance(cmd_object, DynamicCommand | DynamicGroup):
            message = f"Unable to lazily load command `cmd` from: {path}"
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

    from dda.utils.fs import temp_directory

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

    from dda.utils.fs import Path, temp_directory
    from dda.utils.process import EnvVars

    # https://docs.astral.sh/uv/reference/cli/#uv-sync
    command = [
        "sync",
        "--frozen",
        # Prevent synchronizing the project itself because some required dependencies
        # have extension modules. On Windows, files cannot be modified while they are
        # in use. This also affects the entry point script `dda.exe`.
        "--no-install-project",
        "--inexact",
    ]
    for feature in features:
        command.extend(["--only-group", feature])

    with temp_directory() as temp_dir:
        data_dir = Path(sysconfig.get_path("data")) / "dda-data"
        for filename in ("uv.lock", "pyproject.toml"):
            data_file = data_dir / filename
            shutil.copy(data_file, temp_dir)

        env_vars = EnvVars()
        # https://docs.astral.sh/uv/concepts/projects/config/#project-environment-path
        env_vars["UV_PROJECT_ENVIRONMENT"] = prefix
        # Remove warning from output if we happen to display it due to an error
        env_vars.pop("VIRTUAL_ENV", None)

        app.tools.uv.wait(command, message="Synchronizing dependencies", cwd=str(temp_dir), env=env_vars)


def _get_external_plugin_callback(cmd_name: str, executable: str) -> DynamicCommand:
    @dynamic_command(
        name=cmd_name,
        short_help="[external plugin]",
        context_settings={"help_option_names": [], "ignore_unknown_options": True},
    )
    @click.argument("args", nargs=-1)
    @click.pass_context
    def _external_plugin_callback(ctx: click.Context, *, args: tuple[str, ...]) -> None:
        import subprocess

        process = subprocess.run([executable, *args], check=False)
        ctx.exit(process.returncode)

    return _external_plugin_callback


dynamic_command = partial(click.command, cls=DynamicCommand)
dynamic_group = partial(click.group, cls=DynamicGroup)
pass_app = click.pass_obj
