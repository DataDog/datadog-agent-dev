# Install deva Action

-----

This is an action to install deva in your GitHub Actions workflow.

## Usage

You must [use](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepsuses) this action in one of your [jobs](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobs)' [steps](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idsteps):

```yaml
- name: Install deva
  uses: DataDog/datadog-agent-dev@install
```

For strict security guarantees, it's best practice to [pin](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#example-using-versioned-actions) the action to a specific commit (of the [`install` branch](https://github.com/DataDog/datadog-agent-dev/tree/install)) like so:

```yaml
- name: Install deva
  uses: DataDog/datadog-agent-dev@12e0af36a86c69664b8c3589c4e41550581cc07e
```

## Options

Name | Default | Description
--- | --- | ---
`version` | `latest` | The version of deva to install (e.g. `0.4.2`).
`features` | | A space-separated list of features to install (e.g. `feat1 feat2`).

## External consumers

It's possible to use the [install script](https://github.com/DataDog/datadog-agent-dev/blob/install/main.sh) outside of GitHub Actions assuming you set up your environment as follows:

- Set every [option](#options) to an environment variable prefixed by `DEVA_INSTALL_`, uppercased and with hyphens replaced by underscores.
- Set the `DEVA_INSTALL_PATH` environment variable to the directory where you want to install deva.
- Set the `DEVA_INSTALL_PLATFORM` environment variable to the current platform using one of the following values:
    - `linux`
    - `windows`
    - `macos`
- Set the `DEVA_INSTALL_ARCH` environment variable to the current architecture using one of the following values:
    - `x64`
    - `arm64`
- Install [pipx](https://github.com/pypa/pipx) as a fallback installation method for when there is no [standalone binary](https://deva.pypa.io/latest/install/#standalone-binaries) available.
