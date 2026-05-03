# Install and start the current system locally

Status: Current

Last verified: 2026-04-26

This page describes the current local-start paths reflected in the package manifests, CLI, and repo files today.

## Package-shaped CLI path

1. Install or otherwise expose the current `autoclaw` package so the CLI is on `PATH`.
2. Check the environment: `autoclaw doctor`
3. Initialize local config: `autoclaw init`
4. Start the API and bundled console: `autoclaw up`

This page does not hard-code one installer such as `pipx`. The current repo proves the package shape and CLI entrypoint, but install mechanics vary by release or local packaging lane.

## Repo-native contributor path

1. Change into the runtime repo: `cd autoclaw-main`
2. Create a virtual environment: `python -m venv .venv`
3. Install the repo package with dev dependencies: `<venv-python> -m pip install -e .[dev]`
4. Check the environment: `<venv-bin>/autoclaw doctor`
5. Initialize local config: `<venv-bin>/autoclaw init`
6. Start the API and bundled console: `<venv-bin>/autoclaw up`

## Path notes

- on Windows, `<venv-python>` is `.venv\\Scripts\\python` and `<venv-bin>/autoclaw` is `.venv\\Scripts\\autoclaw`
- on POSIX, `<venv-python>` is `.venv/bin/python` and `<venv-bin>/autoclaw` is `.venv/bin/autoclaw`

## Current facts

- current config/data defaults come from `platformdirs`, not from one Linux-only hard-coded path
- Windows example config path: `C:\\Users\\<user>\\AppData\\Local\\autoclaw\\config.toml`
- Linux example config path: `~/.config/autoclaw/config.toml`
- Windows example editable definitions root: `C:\\Users\\<user>\\AppData\\Local\\autoclaw\\definitions`
- Linux example editable definitions root: `~/.config/autoclaw/definitions`
- default local DB: SQLite in the AutoClaw data dir
- default API bind: `127.0.0.1:8123`

## Evidence

- inspected code in `autoclaw-main/apps/api/app/cli.py`
- inspected code in `autoclaw-main/apps/api/app/paths.py`
- inspected package manifest in `autoclaw-main/pyproject.toml`
- inspected repo automation in `autoclaw-main/Makefile`
