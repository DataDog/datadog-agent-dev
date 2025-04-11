# How to use plugins

-----

Every level of commands looks for executables on PATH that start with `dda-`, with every subcommand separated by a single hyphen.

For example, if you have an executable `dda-foo` in your PATH, you can run it with:

```
dda foo
```

The help text of `dda` would contain the following:

```
foo     [external plugin]
```

If you wanted to add a subcommand to the `config` command, you could create an executable `dda-config-bar` in your PATH and then run:

```
dda config bar
```

Every level of commands within the executable name must exist in the main `dda` CLI. So, for example, an executable named `dda-foo-bar` would be invalid because `foo` is not an existing top-level command.
