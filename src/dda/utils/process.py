# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Any, NoReturn

from dda.utils.platform import PLATFORM_ID

if TYPE_CHECKING:
    import subprocess
    from types import TracebackType

    from dda.cli.application import Application


class SubprocessRunner:
    """
    A class for managing the execution of external commands. This is available as the
    [`Application.subprocess`][dda.cli.application.Application.subprocess] property.
    """

    def __init__(self, app: Application) -> None:
        self.__app = app

    def run(self, command: list[str] | str, **kwargs: Any) -> subprocess.CompletedProcess:
        """
        Run a command and wait for it to complete.

        The `check` keyword argument defaults to `True`. When set to `True` and the command exits with a non-zero exit
        code, the application will [abort][dda.cli.application.Application.abort] using the command's exit code rather
        than raising an exception.

        Parameters:
            command: The command to run.

        Returns:
            The completed process.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to [`subprocess.run`][subprocess.run].
        """
        import subprocess

        command, kwargs = self.__sanitize_arguments(command, **kwargs)
        check = kwargs.pop("check", True)

        try:
            process = subprocess.run(command, **kwargs)  # noqa: PLW1510
        except FileNotFoundError:
            self.__app.abort(f"Executable `{command[0]}` not found: {command}")

        if check and process.returncode:
            if process.stderr or process.stdout:
                # Callers might not want to merge both streams so try stderr first
                self.__app.display_critical(process.stderr or process.stdout)

            self.__app.abort(f"Command failed with exit code {process.returncode}: {command}")

        return process

    def capture(self, command: list[str] | str, *, cross_streams: bool = True, **kwargs: Any) -> str:
        """
        Run a command and capture its output.

        Parameters:
            command: The command to run.
            cross_streams: Whether to merge the command's standard error stream into its standard output stream.

        Returns:
            The command's standard output.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`run`][dda.utils.process.SubprocessRunner.run]
                method.
        """
        import subprocess

        kwargs.setdefault("encoding", "utf-8")
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT if cross_streams else subprocess.PIPE
        return self.run(command, **kwargs).stdout

    def wait(self, command: list[str] | str, *, message: str = "", **kwargs: Any) -> None:
        """
        Run a command and wait for it to complete. By default, the command output is hidden but will be displayed if
        the configured verbosity level is at least [`Verbosity.VERBOSE`][dda.config.constants.Verbosity.VERBOSE]. Under
        that circumstance, this method is a mere pass-through to the [`run`][dda.utils.process.SubprocessRunner.run]
        method.

        Parameters:
            command: The command to run.
            message: The message to display while the command is running. Has no effect if the verbosity level is
                less than [`Verbosity.VERBOSE`][dda.config.constants.Verbosity.VERBOSE].

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`run`][dda.utils.process.SubprocessRunner.run]
                or [`capture`][dda.utils.process.SubprocessRunner.capture] methods.
        """
        if self.__app.config.terminal.verbosity >= 1:
            self.run(command, **kwargs)
        else:
            with self.__app.status(self.__app.style_waiting(message or f"Running: {command}")):
                self.capture(command, **kwargs)

    def exit_with(self, command: list[str], **kwargs: Any) -> NoReturn:
        """
        Run a command and [abort][dda.cli.application.Application.abort] with the command's exit code.

        Parameters:
            command: The command to run.

        Other parameters:
            **kwargs: Additional keyword arguments to pass to the [`run`][dda.utils.process.SubprocessRunner.run]
                method.
        """
        process = self.run(command, check=False, **kwargs)
        self.__app.abort(code=process.returncode)

    if sys.platform == "win32":

        def replace_current_process(self, command: list[str]) -> NoReturn:
            self.exit_with(command)

        def spawn_daemon(self, command: list[str] | str, **kwargs: Any) -> None:
            """
            Spawn a daemon process that is detached from the current process.

            Parameters:
                command: The command to run.

            Other parameters:
                **kwargs: Additional keyword arguments to pass to the [`Popen`][subprocess.Popen] constructor.
            """
            import subprocess

            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
            )
            kwargs["stdin"] = subprocess.DEVNULL
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL
            kwargs["close_fds"] = True
            command, kwargs = self.__sanitize_arguments(command, **kwargs)
            subprocess.Popen(command, **kwargs)

    else:

        def replace_current_process(self, command: list[str]) -> NoReturn:  # noqa: PLR6301
            os.execvp(command[0], command)  # noqa: S606

        def spawn_daemon(self, command: list[str] | str, **kwargs: Any) -> None:
            """
            Spawn a daemon process that is detached from the current process.

            Parameters:
                command: The command to run.

            Other parameters:
                **kwargs: Additional keyword arguments to pass to the [`Popen`][subprocess.Popen] constructor.
            """
            import subprocess

            kwargs["start_new_session"] = True
            kwargs["stdin"] = subprocess.DEVNULL
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL
            kwargs["close_fds"] = True
            command, kwargs = self.__sanitize_arguments(command, **kwargs)
            subprocess.Popen(command, **kwargs)

    @staticmethod
    def __sanitize_arguments(command: list[str] | str, **kwargs: Any) -> tuple[list[str] | str, dict[str, Any]]:
        if kwargs.get("shell", False):
            return command, kwargs

        if PLATFORM_ID == "windows":
            # Manually locate executables on Windows to avoid multiple cases in which `shell=True` is required:
            #
            # - If the `PATH` environment variable has been modified, see:
            #   https://github.com/python/cpython/issues/52803
            # - Executables that do not have the extension `.exe`, see:
            #   https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw
            if isinstance(command, list):
                import shutil

                executable = command[0]
                command = [shutil.which(executable) or executable, *command[1:]]
        elif isinstance(command, str):
            import shlex

            return shlex.split(command), kwargs

        return command, kwargs


class EnvVars(dict):
    """
    This class is a snapshot of the current process' environment variables at the time of instantiation.

    Setting environment variables for [subprocesses][dda.utils.process.SubprocessRunner] becomes easy, rather than
    having to manually make a copy of the current environment variables and updating it:

    ```python
    app.subprocess.run([...], env=EnvVars({"FOO": "bar"}))
    ```

    Instances may also be used as a context manager to temporarily update [`os.environ`][os.environ] for the current
    process:

    ```python
    with EnvVars({"FOO": "bar"}):
        ...
    ```

    /// warning
    It's undesirable to persist instances for long periods of time because the environment variables may change
    during the lifetime of the instance.
    ///

    Parameters:
        env_vars: Additional environment variables to include in the snapshot. These override existing environment
            variables and are unaffected by the `include` and `exclude` filtering parameters.
        include: A list of [glob patterns][fnmatch.fnmatch] used to include environment variables in the snapshot.
        exclude: A list of [glob patterns][fnmatch.fnmatch] used to exclude environment variables from the snapshot.
            This takes precedence over the `include` parameter.
    """

    def __init__(
        self,
        env_vars: dict[str, str] | None = None,
        *,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> None:
        super().__init__(os.environ)
        self.old_env = dict(self)

        if include:
            from fnmatch import fnmatch

            self.clear()
            for env_var, value in self.old_env.items():
                for pattern in include:
                    if fnmatch(env_var, pattern):
                        self[env_var] = value
                        break

        if exclude:
            from fnmatch import fnmatch

            for env_var in list(self):
                for pattern in exclude:
                    if fnmatch(env_var, pattern):
                        self.pop(env_var)
                        break

        if env_vars:
            self.update(env_vars)

    def __enter__(self) -> None:
        os.environ.clear()
        os.environ.update(self)

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
