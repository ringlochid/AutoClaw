# Packaging, CLI, and install

Status: Reference

Last verified: 2026-05-12

AutoClaw ships as the `autoclaw` Python package.

## Package facts

- package name: `autoclaw`
- script: `autoclaw = "autoclaw.cli:main"`
- packaged resources include definitions, prompt assets, and systemd templates

## CLI facts

This page is the packaging and install overview. For the exact command groups and config precedence, see [CLI surface and config precedence](cli-surface-and-config-precedence.md).

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

## Local defaults

- default DB: SQLite through `sqlite+aiosqlite`
- default host: `127.0.0.1`
- default port: `18125`
- default config and data dirs come from `platformdirs`
- non-test environments require public and internal API keys

For verification lanes, see [Verify an install and runtime](verify-current-install-and-runtime.md) and [Run Docker-backed Postgres verification](../maintainers/run-docker-postgres-verification.md).
