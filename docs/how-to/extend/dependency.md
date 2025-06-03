# How to add or bump a dependency?

-----

The various dependencies used by `dda` are defined in the `pyproject.toml` file at the root of the repository.

## Identify your dependency

### Local command

Any new dependency for a native local command can be added in the main  `dependency` group `pyproject.toml` file:
/// tab | :octicons-file-code-16: .pyproject.toml
```toml
dependencies = [
  "ada-url~=1.15.3",
  "click~=8.1",
  "datadog-api-client~=2.34",
  "dep-sync~=0.1",
  ...
]
```
///

### Legacy invoke command

For migration reasons, we have several dependency groups corresponding to different build images (`legacy-btf-gen` or `legacy-e2e`) or group of invoke tasks (`legacy-tasks` or `legacy-release`). 

/// tab | :octicons-file-code-16: .pyproject.toml
```toml
[dependency-groups]
legacy-constraints = [
    "azure-identity==1.14.1",
    "wheel==0.40.0",
]
legacy-build = [
    "boto3==1.38.8",
    ...   
]
```
///

So you need to identify on which group you want to put or bump your dependency first.

## Update the dependency

Now you can update the `pyproject.toml` file with your dependency and its version.

Don't forget to update the `uv.lock` file by running
```bash
uv lock
```
Create a PR and ask for a review.

## Create a new release

Create a PR bumping the version, like on this [example](https://github.com/DataDog/datadog-agent-dev/pull/110).
Do not forget to update the changelog regarding the changes included in this version.

## Update buildimages

Bump the new `dda` version in the `datadog-agent-buildimages` repository, see [example](https://github.com/DataDog/datadog-agent-buildimages/pull/856).
