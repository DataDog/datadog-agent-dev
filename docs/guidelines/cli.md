# CLI guidelines

-----

## Command hierarchy

Prefer organizing commands into a deeply nested hierarchy rather than a flat structure. For example, rather than a hypothetical `dda fetch-ci-artifacts` command, prefer `dda ci artifacts fetch`.

## Responsiveness

### Lazy imports

Always use lazy imports for CLI commands. Although commands and command groups are [loaded lazily][dda.cli.base.DynamicGroup], there are two situations in which imports outside of the `cmd` callbacks can influence responsiveness:

- Displaying the help text of a command group will load all subcommands.
- Executing a command will load all parent command groups.

Lazy imports should also be preferred in most other situations. The exceptions are:

1. Modules that are always imported for use by the CLI framework itself (e.g. `click`, [`dda.utils.fs`](../reference/api/fs.md)).
2. Standard library modules that are both used frequently and have a sub-millisecond startup overhead (e.g. `os`, `sys`, `functools`).
3. Modules that must only be imported in the global scope like `typing` ([for now](https://peps.python.org/pep-0781/)) and `__future__`.
4. Lazily importing within functions that would be called in a tight loop. In this case, import normally and refactor logic such that the function itself is only imported when needed.

/// note
Exceptions 1-3 will be enforced by static analysis soon: https://github.com/astral-sh/ruff/issues/17118
///

### User feedback

Never leave users without output for more than a second. Before performing potentially long-running operations, notify the user somehow such as using the [`Application.display_waiting`][dda.cli.application.Application.display_waiting] or [`Application.status`][dda.cli.application.Application.status] methods.
