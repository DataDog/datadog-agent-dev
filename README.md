# Install dda Action

-----

This is an action to install dda in your GitHub Actions workflow.

## Usage

You must [use](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepsuses) this action in one of your [jobs](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobs)' [steps](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idsteps):

```yaml
- name: Install dda
  uses: DataDog/datadog-agent-dev@install
```

For strict security guarantees, it's best practice to [pin](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#example-using-versioned-actions) the action to a specific commit (of the [`install` branch](https://github.com/DataDog/datadog-agent-dev/tree/install)) like so:

```yaml
- name: Install dda
  uses: DataDog/datadog-agent-dev@e1806a36cb1da98f3a4852c6620b628bc31d81b6
```

## Options

Name | Default | Description
--- | --- | ---
`version` | `latest` | The version of dda to install (e.g. `0.5.0`).
`features` | | A space-separated list of features to install (e.g. `feat1 feat2`).

## External consumers

It's possible to use the [install script](https://github.com/DataDog/datadog-agent-dev/blob/install/main.sh) outside of GitHub Actions assuming you set up your environment as follows:

- Set every [option](#options) to an environment variable prefixed by `DDA_INSTALL_`, uppercased and with hyphens replaced by underscores.
- Set the `DDA_INSTALL_PATH` environment variable to the directory where you want to install dda.
- Set the `DDA_INSTALL_PLATFORM` environment variable to the current platform using one of the following values:
    - `linux`
    - `windows`
    - `macos`
- Set the `DDA_INSTALL_ARCH` environment variable to the current architecture using one of the following values:
    - `x64`
    - `arm64`
- Install [pipx](https://github.com/pypa/pipx) as a fallback installation method for when there is no [standalone binary](https://datadoghq.dev/datadog-agent/setup/#standalone-binaries) available.
