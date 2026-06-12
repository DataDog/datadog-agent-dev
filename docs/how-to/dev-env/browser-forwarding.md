# Browser forwarding

When a command inside a dev container opens a URL (for example `ddtool auth gitlab login`),
`dda` automatically forwards it to the host's default browser — including handling OAuth callback
redirects that must reach a service running inside the container.

## How it works

A **browser proxy daemon** runs on the host and listens on a shared port. Each container has a
small **`xdg-open` script** mounted at `/usr/local/bin/xdg-open` that forwards open requests to
the daemon over HTTP via `host.docker.internal`.

```
Container                              Host
──────────────────────────────         ──────────────────────────────────────
tool calls xdg-open <url>
  └─ xdg-open (dda script)
       └─ HTTP → proxy daemon  ──────► 1. detect OAuth redirect_uri → localhost:{port}
                                       2. set up SSH tunnel for the callback port
                                       3. open URL in host browser
                                            │
OAuth provider redirects to                 │ SSH tunnel
  localhost:{callback_port}   ◄─────────────┘
  (forwarded to container)
```

For OAuth flows, the proxy parses the URL for a `redirect_uri` pointing at `localhost` and
establishes an SSH local port forward **before** opening the browser, so the callback from the
provider reaches the service inside the container.

## Lifecycle

The daemon is started on `dda env dev start` and is intentionally kept running across container
restarts — it is shared by all running containers. All containers share the same daemon instance,
each identified by their own SSH port embedded in the `xdg-open` script at container start time.
