# Creating a command

-----

We will create a command `dda agent-release data` that shows Agent release information.

## Structure

If you run the root [`dda`](../../reference/cli/commands.md#dda) command, you'll notice that the subcommands are directories within the [src/dda/cli](https://github.com/DataDog/datadog-agent-dev/tree/main/src/dda/cli) directory:

```
<<<DDA_ROOT_TREE>>>
```

Every command and command group is defined as a Python package with an `__init__.py` file containing a function `cmd` that represents the command or command group. A command is a function decorated with [`@dynamic_command`][dda.cli.base.dynamic_command] that performs a user-requested action and a command group is a function decorated with [`@dynamic_group`][dda.cli.base.dynamic_group] that groups commands together.

## Group

First, let's create the `dda agent-release` command group:

/// tab | :octicons-file-code-16: src/dda/cli/agent_release/\_\_init\_\_.py
```python
from __future__ import annotations

from dda.cli.base import dynamic_group


@dynamic_group(short_help="Agent release-related commands")
def cmd() -> None:
    """
    Commands related to managing Agent releases.
    """
```
///

/// note
Directory names containing multiple words must be separated by underscores. For example, the `agent-release` command group is located in the `src/dda/cli/agent_release` directory.
///

Now running the `dda` command will show the `agent-release` command group:

```console
$ dda
...
╭─ Commands ────────────────────────────────────╮
│ agent-release  Agent release-related commands │
...
```

## Initial command

Next, let's create the initial `dda agent-release data` command and have it [display a message][dda.cli.application.Application.display]:

/// tab | :octicons-file-code-16: src/dda/cli/agent_release/data/\_\_init\_\_.py
```python
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="Show Agent release data",
)
@pass_app
def cmd(app: Application) -> None:
    """
    Show Agent release data.
    """
    app.display("Agent release data")
```
///

Now running the `dda agent-release data` command will show:

```console
$ dda agent-release data
Agent release data
```

## Requiring dependencies

Fetching the Agent's [`release.json`](https://github.com/DataDog/datadog-agent/blob/main/release.json) file requires using an HTTP client. Add the `http` [feature][dda.cli.base.DynamicCommand] to the command to make sure dependencies such as `httpx` are available:

/// tab | :octicons-file-code-16: src/dda/cli/agent_release/data/\_\_init\_\_.py
```python hl_lines="13 20-30"
from __future__ import annotations

from typing import TYPE_CHECKING

from dda.cli.base import dynamic_command, pass_app

if TYPE_CHECKING:
    from dda.cli.application import Application


@dynamic_command(
    short_help="Show Agent release data",
    features=["http"],
)
@pass_app
def cmd(app: Application) -> None:
    """
    Show Agent release data.
    """
    import httpx

    base = "https://raw.githubusercontent.com"
    repo = "DataDog/datadog-agent"
    branch = "main"
    path = "release.json"
    with app.status("Fetching Agent release data"):
        response = httpx.get(f"{base}/{repo}/{branch}/{path}")

    response.raise_for_status()
    app.display_table(response.json())
```
///

Running the command will now show the Agent release data:

```console
$ dda agent-release data
┌───────────────────┬────────────────┐
│ base_branch       │ main           │
│ current_milestone │ 7.66.0         │
│ last_stable       │ ┌───┬────────┐ │
│                   │ │ 6 │ 6.53.1 │ │
│                   │ │ 7 │ 7.64.3 │ │
│                   │ └───┴────────┘ │
...
```
