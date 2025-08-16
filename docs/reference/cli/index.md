# CLI

-----

## Verbosity

The amount of displayed output is controlled solely by the `-v`/`--verbose` (environment variable [`AppEnvVars.VERBOSE`][dda.config.constants.AppEnvVars.VERBOSE]) and `-q`/`--quiet` (environment variable [`AppEnvVars.QUIET`][dda.config.constants.AppEnvVars.QUIET]) [root options](commands.md#dda).

The levels are defined by the [`Verbosity`][dda.config.constants.Verbosity] enum.

## Tab completion

Completion is achieved by saving a script and then executing it as a part of your shell's startup sequence.

Afterward, you'll need to start a new shell in order for the changes to take effect.

/// tab | zsh
Save the script somewhere:

```console
_DDA_COMPLETE=zsh_source dda > ~/.dda-complete.zsh
```

Source the file in `~/.zshrc`:

```console
. ~/.dda-complete.zsh
```
///

/// tab | bash
Save the script somewhere:

```console
_DDA_COMPLETE=bash_source dda > ~/.dda-complete.bash
```

Source the file in `~/.bashrc` (or `~/.bash_profile` if on macOS):

```console
. ~/.dda-complete.bash
```
///

/// tab | fish
Save the script in `~/.config/fish/completions`:

```console
_DDA_COMPLETE=fish_source dda > ~/.config/fish/completions/dda.fish
```
///
