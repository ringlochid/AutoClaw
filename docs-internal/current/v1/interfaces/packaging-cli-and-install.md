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

- `apps/api/src/autoclaw/interfaces/cli/main.py` as the packaged re-export
- `apps/api/src/autoclaw/interfaces/cli/__init__.py` as the legacy `app.cli` compatibility surface
- `apps/api/src/autoclaw/interfaces/cli/**` as the current Click + Rich shell implementation

This page is the packaging/install overview. For the exact current command groups and config precedence, see `cli-surface-and-config-precedence.md`.

Current surface includes:

- `autoclaw init`
- `autoclaw serve`
- `autoclaw onboard`
- `autoclaw configure`
- `autoclaw doctor`
- `autoclaw config path`
- `autoclaw config show`
- `autoclaw db upgrade`
- `autoclaw db reset`
- `autoclaw openclaw check`
- `autoclaw openclaw setup`
- `autoclaw openclaw doctor`
- `autoclaw service render`
- `autoclaw service install`
- `autoclaw service uninstall`
- `autoclaw service start`
- `autoclaw service stop`
- `autoclaw service restart`
- `autoclaw service status`

Current note:

- the managed service implementation in this checkout is Linux `systemd --user`

## Current local defaults

- default DB: SQLite through `sqlite+aiosqlite`
- default host: `127.0.0.1`
- default port: `18125`
- default config and data dirs come from `platformdirs`
- non-test environments require public and internal API keys

## Evidence

Inspected code:

- `apps/api/src/autoclaw/config.py`
- `apps/api/src/autoclaw/paths.py`
- `apps/api/src/autoclaw/interfaces/cli/__init__.py`
- `apps/api/src/autoclaw/interfaces/cli/**`
- `apps/api/src/autoclaw/interfaces/cli/main.py`
- `apps/api/src/autoclaw/platform/managed_services/resources/systemd/autoclaw.service`
- `pyproject.toml`

Inspected tests:

- `apps/api/tests/unit/test_cli.py`
- `apps/api/tests/unit/test_package_entrypoints.py`

## Design pointer

For the target CLI, API, and package split, see `../../../design/v1/interfaces/cli-api-and-package-shape.md` and `../../../design/v1/how-to/install-and-onboard.md`.

For current verification lanes, see `../operations/verify-current-install-and-runtime.md` and `../operations/run-docker-postgres-verification.md`.
