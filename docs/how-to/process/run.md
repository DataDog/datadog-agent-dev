# How to run executables

-----

The [`Application.subprocess`][dda.cli.application.Application.subprocess] property is the preferred way to run and
capture the output of external commands.

```python
import click

from dda.cli.base import dynamic_command, pass_app


@dynamic_command()
@pass_app
def cmd(app: Application) -> None:
    # call methods on app.subprocess
```

## Running commands

The [`SubprocessRunner.run`][dda.utils.process.SubprocessRunner.run] method is used to run a command and wait for it to
complete.

```python
app.subprocess.run(["command", "arg1", "arg2"])
```

## Capturing output

The [`SubprocessRunner.capture`][dda.utils.process.SubprocessRunner.capture] method is used to run a command and capture
its output.

```python
stdout = app.subprocess.capture(["command", "arg1", "arg2"])
```

## Running a final command

The [`SubprocessRunner.exit_with`][dda.utils.process.SubprocessRunner.exit_with] method is used to run a
command and exit the current process with the command's exit code.

```python
app.subprocess.exit_with(["command", "arg1", "arg2"])
```
