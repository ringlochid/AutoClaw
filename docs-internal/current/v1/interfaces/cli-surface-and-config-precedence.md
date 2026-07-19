# Current CLI surface and configuration

Status: Current

Last verified: 2026-07-19

The installed command is `autoclaw`. Commands are non-interactive unless they invoke a provider's own identity flow.

## Passive status

`autoclaw` and `autoclaw status` print the same read-only local summary. They read the selected config and provider settings. They do not contact providers, inspect authentication, test reachability, start a service, or change local state. Unchecked facts are reported as `not_checked`.

## Command groups

- `autoclaw init` writes local config and creates or verifies the exact database schema
- `autoclaw serve` runs the loopback API
- `autoclaw setup` gives setup guidance or configures one selected provider
- `autoclaw providers list|status|check|configure|set-default|login|logout`
- `autoclaw config path|show`
- `autoclaw db upgrade|reset`
- `autoclaw definitions import`
- `autoclaw task-compose start`
- `autoclaw service render|install|uninstall|start|stop|restart|status`

`db upgrade` keeps its compatibility name, but it creates an empty current schema or verifies an exact current schema. It does not migrate a legacy runtime. `db reset` is the destructive schema-change path.

## Provider setup

Codex and Claude are managed integrations. OpenClaw is an experimental user-managed compatibility integration and remains selectable, including as the default.

The first configured provider becomes the default when no default exists. Later configuration does not silently replace an existing default; use `providers set-default`.

`providers status` is passive. `providers check` is the explicit bounded diagnostic and does not run an agent task. Codex login and logout use the native Codex CLI found on the service path. Claude and OpenClaw report their user-owned identity instructions instead of mutating those products.

OpenClaw users maintain their own `openclaw.json` and point it at the compatibility Node MCP endpoint. AutoClaw does not inject that configuration.

Provider configuration and identity changes are CLI-owned. The HTTP API and browser console do not expose provider mutation.

## Configuration precedence

The CLI `--config` option selects the TOML file for that command. Without it, `AUTOCLAW_CONFIG` or the platform default path is used.

For settings values, explicit constructor values win, then `AUTOCLAW_*` environment values, then TOML, then file secrets, then built-in defaults. Nested environment names use `__`. AutoClaw does not load an implicit `.env` file.

The API host must be loopback. The default port is `18125`. SQLite is the default database; PostgreSQL requires a dedicated non-system schema.

## Evidence

- `apps/api/src/autoclaw/interfaces/cli/root.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/`
- `apps/api/src/autoclaw/interfaces/cli/providers/`
- `apps/api/src/autoclaw/config.py`
- `apps/api/tests/integration/public_surfaces/root_cli/`
