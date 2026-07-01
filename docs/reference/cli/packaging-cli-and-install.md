# Packaging, CLI, and install

AutoClaw ships as the `autoclaw` Python package and is published as the root release artifact.

## Package facts

- package name: `autoclaw`
- script: `autoclaw = "autoclaw.interfaces.cli.main:main"`
- packaged resources include definitions, prompt assets, and systemd templates

## Supported install lanes

- primary public lane: `pipx install autoclaw`
- primary public Postgres lane: `pipx install "autoclaw[postgres]"`
- secondary public lane: `uv tool install autoclaw`
- secondary public Postgres lane: `uv tool install "autoclaw[postgres]"`
- contributor/dev lane: editable repo install rather than the published package path

The `pipx` path is the default beginner story. The `uv` path installs the same published package shapes and is supported as a secondary tool-install lane. Editable repo checkout is for AutoClaw contributors and local development, not the main public install story.

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

## Service support note

- the fully supported managed-service implementation in this checkout is Linux with `systemd --user`
- distro support is capability-based systemd user-service support, not a separate packaged binary per distro
- macOS `launchd` and Windows Scheduled Task managers are not shipped v1 parity in this checkout
- `autoclaw serve` remains the foreground runner for local host proof and service-manager execution

## Local defaults

- default DB: SQLite through `sqlite+aiosqlite`
- default host: `127.0.0.1`
- default port: `18125`
- default config and data dirs come from `platformdirs`
- non-test environments require public and internal API keys

For the exact install procedure, see [Install and start locally](install-and-start-local.md). For verification lanes, see [Verify the current install and runtime](verify-current-install-and-runtime.md) and [Run Docker-backed Postgres verification](../maintainers/run-docker-postgres-verification.md).
