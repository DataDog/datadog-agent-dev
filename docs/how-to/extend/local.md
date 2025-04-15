# How to add local commands

-----

The CLI dynamically discovers commands within the current directory under `.dda/extend/commands`. Most commonly, there is only a single `run` command group defined here that contains all the commands.

For example, if you wanted to add a `dda run foo bar` command, you could add the following files:

```
.dda/extend/commands/run/foo/
├── __init__.py
└── bar
    └── __init__.py
```

The `foo` command group might look like this:

/// tab | :octicons-file-code-16: .dda/extend/commands/run/foo/\_\_init\_\_.py
```python
from dda.cli.base import dynamic_group


@dynamic_group(short_help="Foo commands")
def cmd() -> None:
    """
    Long description of the `dda run foo` command group.
    """
```
///

The `bar` command might look like this:

/// tab | :octicons-file-code-16: .dda/extend/commands/run/foo/bar/\_\_init\_\_.py
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
///

/// tip
See [the tutorial](../../tutorials/cli/create-command.md) for more information about creating commands.
///

## Importing utilities

The `.dda/extend/pythonpath` directory is added to the Python search path. For example, if you have the following structure:

```
.dda/extend/pythonpath/
└── utils/
    ├── __init__.py
    └── foo.py
```

Commands can import the `foo` module like this:

```python
from utils import foo
```
