# How to add local commands

-----

The CLI dynamically discovers commands within the current directory under `.dda/scripts`. Most commonly, there is only a single `run` command group defined here that contains all the commands.

Every command and command group is defined as a Python package with an `__init__.py` file and a function `cmd` that defines the command or command group.

For example, if you wanted to add a `dda run foo bar` command, you could add the following files:

```
.dda/scripts/run/foo/
├── __init__.py
└── bar
    └── __init__.py
```

The `.dda/scripts/run/foo/__init__.py` file might define the following command group:

```python
from __future__ import annotations

from dda.cli.base import dynamic_group


@dynamic_group(
    short_help="Foo commands",
)
def cmd() -> None:
    pass
```

The `.dda/scripts/run/foo/bar/__init__.py` file might define the following command:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(short_help="Bar command")
@pass_app
def cmd(app: Application) -> None:
    """
    Long description of the command.
    """
    app.display("Running bar command")
```

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
