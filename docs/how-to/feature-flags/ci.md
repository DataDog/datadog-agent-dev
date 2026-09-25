# How to configure feature flags in CI

-----

The `dda` CLI can evaluate feature flags during CI runs. To enable this, configure how `dda` gets the client token.

## Client token

Set `DDA_FEATURE_FLAGS_CLIENT_TOKEN` to pass the token directly. Otherwise, set a command that prints it:

```toml
[feature-flags.ci]
token-command = ["vault", "kv", "get", "-field=token", "kv/path/to/secret"]
```

You can also use the `DDA_FEATURE_FLAGS_CI_TOKEN_COMMAND` environment variable, which takes precedence. The command runs without a shell. On Windows the variable isn't split with POSIX rules, so backslashes in paths are kept.

```yaml
variables:
  DDA_FEATURE_FLAGS_CI_TOKEN_COMMAND: vault kv get -field=token kv/path/to/secret
```

## Deprecated variables

`DDA_FEATURE_FLAGS_CI_VAULT_PATH`, `DDA_FEATURE_FLAGS_CI_VAULT_KEY`, their `_MACOS` variants and `DDA_FEATURE_FLAGS_CI_SSM_KEY_WINDOWS` still work but are deprecated. Use a token command instead.

## Notes

- `dda` automatically scopes evaluations with CI context, including job name, job ID, stage, and branch.
- If no token can be retrieved, flags default to the code-provided default.
- For details about how to use feature flags in your code, check [create cli documentation](../../tutorials/cli/create-command.md#using-feature-flags)
