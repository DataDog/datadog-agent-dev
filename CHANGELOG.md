# Changelog

-----

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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
