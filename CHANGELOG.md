# Changelog

-----

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

***Fixed:***

- Relax the allowed version of the `cryptography` dependency

## 0.4.0 - 2025-01-09

***Added:***

- Add `self dep` command group to manage dependencies of the `deva` tool itself
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

- Allow repositories to require specific versions in a `.deva-version` or `.deva/version` file
- Add `--clone` flag to the `env dev start` command to clone repositories rather than using local checkouts
- Add binary releases for all supported platforms

## 0.1.0 - 2024-12-09

***Added:***

- Add `env dev` command group to manage developer environments

## 0.0.1 - 2024-09-24

This is the initial public release.
