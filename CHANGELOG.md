# Changelog

-----

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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
