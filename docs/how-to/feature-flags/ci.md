# How to configure feature flags in CI

-----

The `dda` CLI can evaluate feature flags during CI runs. To enable this, set the appropriate environment variables so `dda` can retrieve the client token from your secret store.

## Required environment variables

Set the variables that match your CI runner OS:

- Linux runners:
  - `DDA_FEATURE_FLAGS_CI_VAULT_PATH`: Vault path of the secret (KV v2)
  - `DDA_FEATURE_FLAGS_CI_VAULT_KEY`: Key within the secret containing the client token

- macOS runners:
  - `DDA_FEATURE_FLAGS_CI_VAULT_PATH_MACOS`: Vault path of the secret (KV v2)
  - `DDA_FEATURE_FLAGS_CI_VAULT_KEY_MACOS`: Key within the secret containing the client token

- Windows runners:
  - `DDA_FEATURE_FLAGS_CI_SSM_KEY_WINDOWS`: Name of the SSM Parameter (WithDecryption) that stores the client token

/// tip
On Linux and macOS, `dda` reads the token from Vault KV v2 using the given path and key. On Windows, it reads the token from AWS SSM Parameter Store using the provided parameter name.
///

## Prefer global CI variables

To avoid repeating configuration across jobs, set these as project or group CI/CD variables so they apply to all jobs. You can define them at the top of `.gitlab-ci.yml`:

```yaml
variables:
  DDA_FEATURE_FLAGS_CI_VAULT_PATH: kv/path/to/dda/feature-flags
  DDA_FEATURE_FLAGS_CI_VAULT_KEY: CLIENT_TOKEN
  DDA_FEATURE_FLAGS_CI_VAULT_PATH_MACOS: kv/path/to/dda/feature-flags
  DDA_FEATURE_FLAGS_CI_VAULT_KEY_MACOS: CLIENT_TOKEN
  DDA_FEATURE_FLAGS_CI_SSM_KEY_WINDOWS: ci.repo-name.my-ssm-parameter-name
```

## Notes

- `dda` automatically scopes evaluations with CI context, including job name, job ID, stage, and branch.
- If the variables are not set or the secret cannot be fetched, flags default to the code-provided default.
- For details about how to use feature flags in your code, check [create cli documentation](../../tutorials/cli/create-command.md#using-feature-flags)
