# Changelog

-----

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

***Added:***

- Pass local Git author details to developer environments
- Mount the Docker socket in the `linux-container` developer environment type

***Fixed:***

- Prevent passing `TERM` environment variable to SSH connections

## 0.12.5 - 2025-05-12

***Fixed:***

- Fix the `inv` command when legacy tasks require user input

## 0.12.4 - 2025-05-07

***Fixed:***

- Allow user input on non-Windows platforms for `app.subprocess` methods that use a pseudo-terminal

## 0.12.3 - 2025-05-04

***Fixed:***

- Most `app.subprocess` methods no longer force the use of a pseudo-terminal when the parent process is not interactive
- Update dependencies to remove spurious warnings on newer versions of Python

## 0.12.2 - 2025-05-03

***Fixed:***

- Fix the `env dev shell` command when using the `linux-container` developer environment type
- Prevent issues on Windows when using the `uv` dependency to upgrade itself

## 0.12.1 - 2025-05-02

***Fixed:***

- Fix the `env dev start` command when using the `linux-container` developer environment type
- Fix the `check` parameter of the `app.subprocess.capture` method

## 0.12.0 - 2025-05-01

***Changed:***

- The `app.subprocess.run` method now uses a pseudo-terminal in order to capture output from subprocesses while displaying it. A new `app.subprocess.attach` method is available which retains the original behavior and should be preferred when subprocesses require user interaction.
- The `app.subprocess.run` method now returns an integer representing the exit code of the completed subprocess call

***Added:***

- Automatically send telemetry for failed subprocesses
- Add `app.subprocess.redirect` method for redirecting the output of a command to a file-like object
- Update dependencies

***Fixed:***

- Properly apply Python path modifications when loading dynamic commands

## 0.11.0 - 2025-04-25

***Added:***

- Switch to traces for telemetry

## 0.10.1 - 2025-04-22

***Fixed:***

- Only show the help text of the `inv` command when no arguments are provided

## 0.10.0 - 2025-04-22

***Changed:***

- The paths used to search for local commands are no longer added to the Python search path and instead a sibling directory `pythonpath` is used

***Added:***

- Add `dda.utils.platform.get_machine_id` function
- Add `dda.utils.date` utilities
- Add `dda.utils.network.http` utilities
- Add proper backoff for the retry utilities
- Add `binary` and `rich` to the global legacy dependencies used for the `inv` command

***Fixed:***

- Properly persist Python search path modifications for local commands when using subprocesses
- Fixed locally running config restoration tests when telemetry is enabled

## 0.9.0 - 2025-04-02

***Added:***

- Add initial dependency features for common functionality (`http`, `github`, `gitlab`)
- Telemetry is now submitted immediately after the command completes rather than a short wait
- Prevent Docker CLI hints/tips output

***Fixed:***

- Fix ignored directory heuristic for finding local commands
- Reduce log verbosity of telemetry daemon
- Fix `self telemetry log show` command when the log file contents do not fit within memory

## 0.8.1 - 2025-04-01

***Fixed:***

- Fix telemetry log API submission
- Support telemetry submission within the `linux-container` developer environment type

## 0.8.0 - 2025-03-26

***Added:***

- Add support for dynamically loading local commands

***Fixed:***

- Properly collect telemetry for the `inv` command on non-Windows platforms

## 0.7.0 - 2025-03-20

***Added:***

- Telemetry now uses logs instead of events

***Fixed:***

- Fix the `self telemetry log remove` command

## 0.6.2 - 2025-03-12

***Fixed:***

- Fix escaping on the non-Windows entry points of prebuilt distributions
- Fix the help text of commands that have dynamic parameters
- Fix the read permissions of the `dda` binary within the PKG installer

## 0.6.1 - 2025-03-10

***Fixed:***

- Fix the read permissions of the `dda` binary on non-Windows platforms

## 0.6.0 - 2025-03-07

***Added:***

- Add `--feat` and `--dep` flags to the `inv` command to install extra features and dependencies

## 0.5.2 - 2025-03-06

***Fixed:***

- Update legacy dependency definitions

## 0.5.1 - 2025-03-05

***Fixed:***

- Remove dynamic installation of `legacy-kernel-matrix-testing` dependencies

## 0.5.0 - 2025-02-25

***Changed:***

- Rename package to `dda`

***Added:***

- Add telemetry collection for Datadog employees
- Update dependencies
- Update prebuilt distributions to use Python 3.12.9

## 0.4.3 - 2025-02-05

***Fixed:***

- Use the proper Python executable when running the `inv` command without dynamic dependencies

## 0.4.2 - 2025-01-26

***Fixed:***

- Repository-specific version files (`.dda-version` or `.dda/version`) now define the minimum required version rather than the exact version

## 0.4.1 - 2025-01-18

***Fixed:***

- Relax the allowed version of the `cryptography` dependency
- Backport dependency update of `pyright`

## 0.4.0 - 2025-01-09

***Added:***

- Add `self dep` command group to manage dependencies of the `dda` tool itself
- Use a lock file for dependency management

## 0.3.0 - 2025-01-03

***Added:***

- Add PKG installer for macOS

***Fixed:***

- The `inv` command now supports the dependencies of tasks defined in the `test-infra-definitions` repo

## 0.2.0 - 2025-01-02

***Changed:***

- Use local versions of repositories rather than remote clones for developer environments by default

***Added:***

- Allow repositories to require specific versions in a `.dda-version` or `.dda/version` file
- Add `--clone` flag to the `env dev start` command to clone repositories rather than using local checkouts
- Add binary releases for all supported platforms

## 0.1.0 - 2024-12-09

***Added:***

- Add `env dev` command group to manage developer environments

## 0.0.1 - 2024-09-24

This is the initial public release.
