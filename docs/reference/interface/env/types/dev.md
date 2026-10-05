# Developer environment interface

-----

Environment types implementing the [`DeveloperEnvironmentInterface`][dda.env.dev.interface.DeveloperEnvironmentInterface] interface may be managed by the [`env dev`](../../../cli/commands.md#dda-env-dev) command group.

::: dda.env.dev.interface.DeveloperEnvironmentConfig
    options:
      show_labels: true
      unwrap_annotated: true

::: dda.env.dev.interface.DeveloperEnvironmentInterface
    options:
      show_labels: true
      show_if_no_docstring: false

## Managed sandboxes

The Linux container environment supports an opt-in `--transport exec` mode for
managed sandboxes. SSH remains the default for local development. Exec mode
requires an image whose entrypoint supports `DD_DEV_ENV_TRANSPORT=exec`, and a
container manager configured with a working native init binary.

```console
dda env dev start --transport exec --shell bash --no-secrets
dda env dev run dda inv test --targets ./pkg/util/log
dda env dev shell
```

This mode uses the container manager to execute as `dd`, keeps `/home/dd` and the
mounted checkout, and persists the transport for subsequent commands. It does
not publish SSH/MCP ports, mount the Docker socket, import host shell or coding
agent state, forward AWS/telemetry credentials, or start browser/editor proxies.
Interactive shells allocate a terminal only when the caller has one. Explicit
extra mounts remain available; review them before adding credentials or sockets.
SSH editor integration and remote cloning are unavailable in exec mode.

In Bits Code, the coding agent should clone/fetch using its existing SCM broker
on the sandbox host, including real release tags needed by Agent's version
lookup. Run build and test commands inside the mounted checkout. Container-local
GitHub API calls and cloud tools still require a separately supported broker;
exec mode does not authenticate these tools or grant additional capabilities.
