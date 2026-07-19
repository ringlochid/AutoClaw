# Current CLI surface and configuration

Status: Current

Last verified: 2026-07-19

The installed command is `autoclaw`. On a terminal, `init` and `setup` are guided. `--non-interactive`, non-TTY input, and `--json` use the deterministic command path without prompts. Other commands remain non-interactive unless they invoke a provider's own identity flow.

## Passive status

`autoclaw` and `autoclaw status` print the same read-only local summary. They read the selected config and provider settings. They do not contact providers, inspect authentication, test reachability, start a service, or change local state. JSON keeps unchecked facts as `not_checked`; human provider status shows one local-only explanation and the exact check command instead of repeating raw unchecked axes.

## Command groups

- `autoclaw init` guides local config and creates or verifies the exact database schema
- `autoclaw serve` runs the loopback API
- `autoclaw setup` guides primary/default provider selection, provider checking and supported login, and optional additional providers
- `autoclaw providers list|status|check|configure|set-default|login|logout`
- `autoclaw config path|show`
- `autoclaw db upgrade|reset`
- `autoclaw definitions import`
- `autoclaw task-compose start`
- `autoclaw service render|install|uninstall|start|stop|restart|status`

`db upgrade` keeps its compatibility name, but it creates an empty current schema or verifies an exact current schema. It does not migrate a legacy runtime. `db reset` is the destructive schema-change path.

## Provider setup

Codex and Claude are managed integrations. OpenClaw is an experimental user-managed compatibility integration and remains selectable, including as the default.

The guided setup flow asks for the primary/default provider. It routes that explicit choice through the same configure and set-default operations exposed by the direct provider commands, then asks whether to configure additional providers without replacing the primary default. A direct `providers configure` fills the default only when none exists; later direct configuration preserves it.

Guided setup checks each selected provider. When Codex reports that authentication is required, it offers the SDK-bundled native Codex login before checking again. Claude and OpenClaw keep their user-owned identity behavior. Each accepted step is committed independently, so cancellation keeps completed selections and rerunning resumes from current config rather than a setup journal.

`providers status` is passive. `providers check` is the explicit bounded diagnostic and does not run an agent task. Human checks render authentication and reachability as confirmed, failed, or not tested; JSON uses the stable enum values. Codex checks directly confirm typed ChatGPT and API-key account state without claiming remote model reachability. Codex login and logout use the SDK-bundled Codex CLI. Claude and OpenClaw report their user-owned identity instructions instead of mutating those products.

Interactive setup, provider status/check, and service status use terminal-aware Rich panels, tables, and semantic colors. Redirected output and `NO_COLOR` use readable plain text. JSON remains undecorated.

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
