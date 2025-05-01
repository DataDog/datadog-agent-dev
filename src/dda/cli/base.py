# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from functools import cached_property, partial
from importlib.util import module_from_spec, spec_from_file_location
from time import perf_counter_ns
from typing import TYPE_CHECKING, Any, cast

import rich_click as click
from click.exceptions import Exit, UsageError
from rich_click.rich_help_formatter import RichHelpFormatter

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.deepest_command_path: str | None = None

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
            group_dir = os.path.join(search_path, _search_path_name(parent_cmd_name))
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
        command_depth = len(self.command_path.split())
        root_ctx = _get_root_ctx(self)
        if root_ctx.deepest_command_path is None or command_depth > len(root_ctx.deepest_command_path.split()):
            root_ctx.deepest_command_path = self.command_path

        app: Application | None = self.obj
        if (
            # The application may not be set if an error occurred very early
            app is not None
            and app.telemetry.enabled
            # The proper exit code only manifests when the top level context exits
            and command_depth == 1
            and self._depth == 1
        ):
            if isinstance(exc_value, Exit):
                # https://github.com/pallets/click/blob/8.1.8/src/click/exceptions.py#L296
                exit_code = exc_value.exit_code
            elif isinstance(exc_value, UsageError):
                # https://github.com/pallets/click/blob/8.1.8/src/click/exceptions.py#L64
                exit_code = 2
            elif isinstance(exc_value, KeyboardInterrupt):
                # Use the non-Windows default value for consistency
                # https://www.redhat.com/en/blog/exit-codes-demystified
                # https://github.com/python/cpython/blob/3.13/Modules/main.c#L731-L754
                exit_code = 130
            else:
                import traceback

                # https://github.com/pallets/click/blob/8.1.8/src/click/exceptions.py#L29
                exit_code = 1
                app.last_error = traceback.format_exc()

            from dda.cli import START_TIME, START_TIMESTAMP
            from dda.utils.platform import join_command_args

            metadata = {
                "cli.command": join_command_args(sys.argv[1:]),
                "cli.exit_code": str(exit_code),
            }
            if last_error := app.last_error.strip():
                # Payload limit is 5MB so we truncate the error message to a little bit less than that
                message_max_length = int(1024 * 1024 * 4.5)
                metadata["error.message"] = last_error[-message_max_length:]

            app.telemetry.trace.span({
                "resource": " ".join(root_ctx.deepest_command_path.split()[1:]) or " ",
                "start": START_TIMESTAMP,
                "duration": perf_counter_ns() - START_TIME,
                "error": 0 if exit_code == 0 else 1,
                "meta": metadata,
            })

        super().__exit__(exc_type, exc_value, tb)


class DynamicCommand(click.RichCommand):
    """
    A subclass of the [`Command`][click.Command] class provided by [rich-click](https://github.com/ewels/rich-click)
    that allows for dynamic help text and dependency management.

    Parameters:
        features: A list of
            [dependency groups](https://packaging.python.org/en/latest/specifications/dependency-groups/) that must be
            satisfied before the command callback can be invoked. These are defined in the
            [`pyproject.toml`](https://github.com/DataDog/datadog-agent-dev/blob/main/pyproject.toml) file.
        dependencies: An arbitrary list of
            [dependencies](https://packaging.python.org/en/latest/specifications/dependency-specifiers/) that must be
            satisfied before the command callback can be invoked.

    Other parameters:
        *args: Additional positional arguments to pass to the [`Command`][click.Command] constructor.
        **kwargs: Additional keyword arguments to pass to the [`Command`][click.Command] constructor.
    """

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
            root_ctx = _get_root_ctx(ctx)
            search_path = root_ctx.search_paths[self.dynamic_path_id]
            pythonpath = _get_pythonpath(search_path)
            with _apply_pythonpath(pythonpath) as applied:
                if applied:
                    from dda.utils.process import EnvVars

                    # The environment variable is required to influence subprocesses
                    with EnvVars({"PYTHONPATH": pythonpath}):
                        return super().invoke(ctx)

        return super().invoke(ctx)

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
    """
    A subclass of the [`Group`][click.Group] class provided by [rich-click](https://github.com/ewels/rich-click)
    that allows for dynamic loading of subcommands.

    Parameters:
        allow_external_plugins: Whether to allow external plugins to be loaded. The default is taken from the
            equivalent property of the parent group.
        subcommand_filter: A function that takes a subcommand name and returns a boolean indicating whether the
            subcommand should be included in the list of subcommands.
        search_path_finder: A function that returns a list of directories to search for subcommands.

    Other parameters:
        *args: Additional positional arguments to pass to the [`Group`][click.Group] constructor.
        **kwargs: Additional keyword arguments to pass to the [`Group`][click.Group] constructor.
    """

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
            _normalize_cmd_name(entry.name)
            for search_path in ctx.search_paths.values()
            for entry in os.scandir(search_path)
            if "-" not in entry.name and os.path.isfile(os.path.join(entry.path, "__init__.py"))
        )
        if not _building_docs() and ctx.allow_external_plugins:
            commands.extend(ctx.external_plugins)

        self.__subcommand_cache = sorted(command for command in commands if self._subcommand_allowed(command))
        return self.__subcommand_cache

    def get_command(self, ctx: DynamicContext, cmd_name: str) -> DynamicCommand | DynamicGroup | None:  # type: ignore[override]
        command: DynamicCommand | DynamicGroup | None = super().get_command(ctx, cmd_name)  # type: ignore[assignment]
        if command is not None:
            return command

        normalized_cmd_name = _normalize_cmd_name(cmd_name)
        if cmd_name != normalized_cmd_name:
            return None

        cmd_name = normalized_cmd_name
        if not self._subcommand_allowed(cmd_name):
            return command

        root_ctx = _get_root_ctx(ctx)
        for i, search_path in ctx.search_paths.items():
            cmd_path = os.path.join(search_path, _search_path_name(cmd_name), "__init__.py")
            if os.path.isfile(cmd_path):
                if i == 0:
                    command = self._lazy_load(cmd_name, cmd_path)
                else:
                    pythonpath = _get_pythonpath(root_ctx.search_paths[i])
                    with _apply_pythonpath(pythonpath):
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


def _normalize_cmd_name(cmd_name: str) -> str:
    return cmd_name.replace("_", "-")


def _search_path_name(cmd_name: str) -> str:
    return cmd_name.replace("-", "_")


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


def _get_root_ctx(ctx: click.Context) -> DynamicContext:
    while ctx.parent is not None:
        ctx = ctx.parent

    return cast(DynamicContext, ctx)


def _get_pythonpath(root_search_path: str) -> str:
    # Directory alongside the top-level search path
    return os.path.join(os.path.dirname(root_search_path), "pythonpath")


@contextmanager
def _apply_pythonpath(pythonpath: str) -> Generator[bool, None, None]:
    if os.path.isdir(pythonpath):
        sys.path.insert(0, pythonpath)
        try:
            yield True
        finally:
            sys.path.pop(0)
    else:
        yield False


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
"""
A decorator wrapping [`click.command`][click.command] that configures a [`DynamicCommand`][dda.cli.base.DynamicCommand]. Example:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Command")
@pass_app
def cmd(app: Application) -> None:
    \"""
    Long description of the command.
    \"""
    app.display("Running command")
```
"""
dynamic_group = partial(click.group, cls=DynamicGroup)
"""
A decorator wrapping [`click.group`][click.group] that configures a [`DynamicGroup`][dda.cli.base.DynamicGroup]. Example:

```python
from __future__ import annotations

from dda.cli.base import dynamic_group


@dynamic_group(
    short_help="Command group",
)
def cmd() -> None:
    \"""
    Long description of the command group.
    \"""
```
"""
pass_app = click.pass_obj
"""
A partial function that returns a decorator for passing an [`Application`][dda.cli.application.Application] instance
to a command callback.
"""
