# Install and start the current system locally

Status: Current

Last verified: 2026-05-12

This page describes the current local-start paths reflected in the package
manifest, shipped CLI, and repo files today.

## Package-shaped CLI path

1. Install or otherwise expose the current `autoclaw` package so the CLI is on `PATH`.
2. Initialize local config and seeded SQLite state: `autoclaw init`
3. Start the API in the foreground: `autoclaw serve`
4. Optional durable local-service path without systemd: `autoclaw service start`
5. Optional user-service path: `autoclaw service render` or
   `autoclaw service install`

This page does not hard-code one installer such as `pipx`. The current repo
proves the package shape and CLI entrypoint, but install mechanics vary by
release or local packaging lane.

## Repo-native contributor path

1. Change into the repo root: `cd <autoclaw-repo>`
2. Create a virtual environment: `python -m venv .venv`
3. Install the repo package with dev dependencies: `<venv-python> -m pip install -e .[dev]`
4. Initialize local config: `<venv-bin>/autoclaw init`
5. Start the API in the foreground: `<venv-bin>/autoclaw serve`
6. Optional durable local-service path without systemd:
   `<venv-bin>/autoclaw service start`
7. Optional user-service path:
   `<venv-bin>/autoclaw service render` or
   `<venv-bin>/autoclaw service install`

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
- `serve` remains a foreground process that exits with its parent shell/session
- current shipped CLI commands are `init`, `serve`, `db upgrade|reset`, and
  `service render|install|start|stop|restart|status`

## Evidence

- inspected code in `apps/api/app/cli.py`
- inspected code in `apps/api/app/paths.py`
- inspected package manifest in `pyproject.toml`
- inspected CLI tests in `apps/api/tests/unit/test_cli.py`
- inspected repo automation in `Makefile`
