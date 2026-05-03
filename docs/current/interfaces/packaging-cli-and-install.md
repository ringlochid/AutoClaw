# Current packaging, CLI, and install baseline

Status: Current

Last verified: 2026-04-24

The root package manifest is the current authoritative packaging surface.

## Current package facts

Authoritative manifest:

- `autoclaw-main/pyproject.toml`

Current caveat:

- `autoclaw-main/apps/api/pyproject.toml` still exists as older developer-local packaging context and must not be treated as the product package authority

Current root-manifest facts:

- package name: `autoclaw`
- script: `autoclaw = "autoclaw.cli:main"`
- package dir: `apps/api`
- packaged resources include definitions, web assets, Alembic resources, and systemd templates

## Current CLI facts

Current CLI implementation lives in `autoclaw-main/apps/api/app/cli.py`.

This page is the packaging/install overview. For the exact current command groups and config precedence, see `cli-surface-and-config-precedence.md`.

Current surface includes:

- `autoclaw init`
- `autoclaw serve`
- `autoclaw up`
- `autoclaw service *`
- `autoclaw db *`
- `autoclaw doctor`
- `autoclaw config *`
- `autoclaw task-compose start`
- `autoclaw openclaw check`

## Current local defaults

- default DB: SQLite through `sqlite+aiosqlite`
- default host: `127.0.0.1`
- default port: `8123`
- current OpenClaw default URL: `http://127.0.0.1:18789`
- non-test environments require public and internal API keys

## Evidence

Inspected code:

- `autoclaw-main/apps/api/app/config.py`
- `autoclaw-main/apps/api/app/paths.py`
- `autoclaw-main/apps/api/app/cli.py`
- `autoclaw-main/pyproject.toml`

Inspected tests:

- `autoclaw-main/apps/api/tests/unit/test_cli.py`
- `autoclaw-main/apps/api/tests/unit/test_package_entrypoints.py`

## Redesign pointer

For the target CLI/API/package split, see `../../redesign/interfaces/cli-api-and-package-shape.md` and `../../redesign/how-to/install-and-onboard.md`.

For current verification lanes, see `../operations/verify-current-install-and-runtime.md` and `../operations/run-docker-postgres-verification.md`.
