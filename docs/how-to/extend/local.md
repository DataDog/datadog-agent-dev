# How to add local commands

-----

The CLI dynamically discovers commands within the current directory under `.dda/scripts`. Most commonly, there is only a single `run` command group defined here that contains all the commands.

For example, if you wanted to add a `dda run foo bar` command, you could add the following files:

```
.dda/scripts/run/foo/
├── __init__.py
└── bar
    └── __init__.py
```

The `.dda/scripts/run/foo/__init__.py` file might define the following command group:

```python
from dda.cli.base import dynamic_group


@dynamic_group(short_help="Foo commands")
def cmd() -> None:
    """
    Long description of the `dda run foo` command group.
    """
```

The `.dda/scripts/run/foo/bar/__init__.py` file might define the following command:

```python
from dda.cli.base import dynamic_command, pass_app


@dynamic_command(short_help="Bar command")
@pass_app
def cmd(app) -> None:
    """
    Long description of the `dda run foo bar` command.
    """
    app.display("Running bar command")
```

/// tip
See [the tutorial](../../tutorials/cli/create-command.md) for more information about creating commands.
///

## Importing utilities

Any directory starting with `_` will not be considered a command or command group. The `.dda/scripts` directory is added to the Python path, so you can import such private modules. For example, if you have the following structure:

```
.dda/scripts/
└── _utils/
    ├── __init__.py
    └── foo.py
```

You can import the `foo` module like this:

```python
from _utils import foo
```
