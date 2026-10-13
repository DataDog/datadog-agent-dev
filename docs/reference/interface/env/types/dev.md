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

### Bits Code

Use `DD_BITS_CODE=1 dda env dev start --bits-code --shell bash` in Bits Code.
The saved `bits_code` option selects exec transport and sets `DD_BITS_CODE=1`
in the container, including after restarting it. Set the marker on the host
for all DDA commands as well: CLI startup happens before environment options
are resolved. The marker is a behavior hint, never authentication or authority.
Without this opt-in the default remains SSH.

In this mode DDA skips optional update checks and telemetry credential discovery,
and disables interactive terminal behavior. `dda tools ddgl setup` exits with
an actionable error before installing tools or configuring token commands.
Run authenticated GitLab operations on the host with its supported authentication;
use the existing Bits SCM broker for Git operations. No host credentials or
sockets are implicitly forwarded into the container.

The mounted repository must be named `datadog-agent` beside the working
directory from which DDA starts (or select its actual name with `--repo` and
use that name with subsequent commands). Prepare that checkout and its release
tags through the host SCM broker before starting the container.

For sandbox egress interception, the Agent image accepts a caller-provided
read-only trust directory:

```console
DD_BITS_CODE=1 dda env dev start --bits-code --shell bash \
  --volume /path/to/public-trust:/run/codegen-trust:ro
```

The directory must contain `ca-certificates.crt`, `sandbox-proxy-ca.crt`, and
`java-cacerts` exported by the sandbox's public-CA helper. It contains public
trust material only. This mount does not supply identity or credentials.
