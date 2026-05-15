# Current packaging, CLI, and install baseline

Status: Current

Last verified: 2026-05-12

The root package manifest is the current authoritative packaging surface.

## Current package facts

Authoritative manifest:

- `pyproject.toml`

Current root-manifest facts:

- package name: `autoclaw`
- script: `autoclaw = "autoclaw.cli:main"`
- package dir: `apps/api`
- packaged resources include definitions, prompt assets, and systemd templates

## Current CLI facts

The installed entrypoint resolves through:

- `apps/api/autoclaw/cli.py` as the packaged re-export
- `apps/api/app/cli.py` as the current implementation

This page is the packaging/install overview. For the exact current command
groups and config precedence, see `cli-surface-and-config-precedence.md`.

Current surface includes:

- `autoclaw init`
- `autoclaw serve`
- `autoclaw db upgrade`
- `autoclaw db reset`
- `autoclaw service render`
- `autoclaw service install`
- `autoclaw service start`
- `autoclaw service stop`
- `autoclaw service restart`
- `autoclaw service status`

## Current local defaults

- default DB: SQLite through `sqlite+aiosqlite`
- default host: `127.0.0.1`
- default port: `8123`
- default config and data dirs come from `platformdirs`
- non-test environments require public and internal API keys

## Evidence

Inspected code:

- `apps/api/app/config.py`
- `apps/api/app/paths.py`
- `apps/api/app/cli.py`
- `apps/api/autoclaw/cli.py`
- `apps/api/app/resources/systemd/autoclaw.service`
- `pyproject.toml`

Inspected tests:

- `apps/api/tests/unit/test_cli.py`
- `apps/api/tests/unit/test_package_entrypoints.py`

## Redesign pointer

For the target CLI, API, and package split, see
`../../redesign/interfaces/cli-api-and-package-shape.md` and
`../../redesign/how-to/install-and-onboard.md`.

For current verification lanes, see
`../operations/verify-current-install-and-runtime.md` and
`../operations/run-docker-postgres-verification.md`.
