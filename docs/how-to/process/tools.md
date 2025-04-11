# How to use tools

-----

Some executables require special handling to be executed properly. For example, Docker requires a specific environment variable to be set in order to disable noisy CLI hints.

Such executables are available as tools on the [`Application.tools`][dda.cli.application.Application.tools] property. Every tool has the same methods as the [`SubprocessRunner`][dda.utils.process.SubprocessRunner] class (except for the `spawn_daemon` method).

The first argument of commands, the tool name itself, is omitted as it is implicit. For example, to run `docker build`, you can write:

```python
app.tools.docker.run(["build", ".", "--tag", "my-image"])
```
