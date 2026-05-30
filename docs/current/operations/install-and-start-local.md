# Install and start the current system locally

Status: Current

Last verified: 2026-05-28

This page describes the current local-start paths reflected in the package manifest, shipped CLI, and repo files today.

## Package-shaped CLI path

1. Install or otherwise expose the current `autoclaw` package so the CLI is on `PATH`.
2. Run first-run setup: `autoclaw onboard`
3. Verify local state: `autoclaw doctor`
4. Verify the OpenClaw integration side: `autoclaw openclaw check`
5. Start the managed Linux user service: `autoclaw service start`
6. Optional foreground host-proof path: `autoclaw serve`

This page does not hard-code one installer such as `pipx`. The current repo proves the package shape and CLI entrypoint, but install mechanics vary by release or local packaging lane.

## Repo-native contributor path

1. Change into the repo root: `cd <autoclaw-repo>`
2. Create a virtual environment: `python -m venv .venv`
3. Install the repo package with dev dependencies: `<venv-python> -m pip install -e .[dev]`
4. Run first-run setup: `<venv-bin>/autoclaw onboard`
5. Verify local state: `<venv-bin>/autoclaw doctor`
6. Verify the OpenClaw integration side: `<venv-bin>/autoclaw openclaw check`
7. Start the managed Linux user service: `<venv-bin>/autoclaw service start`
8. Optional foreground host-proof path: `<venv-bin>/autoclaw serve`

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
- current shipped service lifecycle is the managed Linux `systemd --user` surface
- current shipped CLI commands also include `onboard`, `configure`, `doctor`, `config path|show`, and `openclaw check|setup|doctor`
- the current shipped onboarding/configuration flow now reconciles both local AutoClaw state and the AutoClaw-owned OpenClaw integration slice
- when the local SQLite runtime comes from an older incompatible schema, `autoclaw onboard` now backs that DB up and reconciles a fresh current-schema runtime DB instead of failing immediately

## Evidence

- inspected code in `apps/api/app/cli.py`
- inspected code in `apps/api/app/paths.py`
- inspected package manifest in `pyproject.toml`
- inspected CLI tests in `apps/api/tests/unit/test_cli.py`
- inspected repo automation in `Makefile`
