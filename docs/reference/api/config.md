# Config reference

-----

Configuration for `dda` itself is stored in a `config.toml` file located by default in one of the following platform-specific directories:

Platform | Directory
--- | ---
macOS | `~/Library/Application Support/dd-agent-dev`
Windows | `%USERPROFILE%\AppData\Local\dd-agent-dev`
Linux | `$XDG_CONFIG_HOME/dd-agent-dev` (the [XDG_CONFIG_HOME](https://specifications.freedesktop.org/basedir-spec/latest/#variables) environment variable defaults to `~/.config` on Linux)

You can select a custom path to the file using the `--config` [root option](../cli/commands.md#dda) or by setting the [ConfigEnvVars.CONFIG][dda.config.constants.ConfigEnvVars.CONFIG] environment variable.

The file can be managed by the [`config`](../cli/commands.md#dda-config) command group.

## Root

::: dda.config.model.RootConfig
    options:
      heading_level: 3

## Environments

::: dda.config.model.env.EnvConfig
    options:
      heading_level: 3

::: dda.config.model.env.DevEnvConfig
    options:
      heading_level: 3

## Git

::: dda.config.model.git.GitConfig
    options:
      heading_level: 3

::: dda.config.model.git.GitUser
    options:
      heading_level: 3

## GitHub

::: dda.config.model.github.GitHubConfig
    options:
      heading_level: 3

::: dda.config.model.github.GitHubAuth
    options:
      heading_level: 3

## Organization

::: dda.config.model.orgs.OrgConfig
    options:
      heading_level: 3
      annotations_path: full

## Storage

::: dda.config.model.storage.StorageDirs
    options:
      heading_level: 3

## Terminal

::: dda.config.model.terminal.TerminalConfig
    options:
      heading_level: 3

::: dda.config.model.terminal.TerminalStyles
    options:
      heading_level: 3

## Update

::: dda.config.model.update.UpdateConfig
    options:
      heading_level: 3

::: dda.config.model.update.UpdateCheckConfig
    options:
      heading_level: 3
      members:
      - period
      - get_period_seconds
