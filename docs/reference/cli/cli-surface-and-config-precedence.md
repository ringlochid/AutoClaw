# CLI surface and configuration precedence

The installed command is `autoclaw`. Commands are non-interactive unless a provider opens its own identity flow.

## Passive front door

Running `autoclaw` without a subcommand is the same as `autoclaw status`. It reads local config and provider selections only. It does not contact providers, inspect provider authentication, start a service, upgrade a database, or write files. Unchecked facts are reported as `not_checked`.

## Command families

| Command | Shipped purpose |
| --- | --- |
| `autoclaw init` | Write config and create or verify the exact current schema. |
| `autoclaw setup` | Show setup guidance or configure one selected provider. |
| `autoclaw status` | Read passive local status. |
| `autoclaw serve` | Run the loopback API in the foreground. |
| `autoclaw config path|show` | Locate or read effective config. |
| `autoclaw providers list|status|check|configure|set-default|login|logout` | Manage provider selection and explicit diagnostics. |
| `autoclaw definitions import` | Publish a definition file. |
| `autoclaw task-compose start` | Start one task from a local task-compose file. |
| `autoclaw db upgrade|reset` | Create or verify the exact schema, or destructively reset it. |
| `autoclaw service render|install|uninstall|start|stop|restart|status` | Manage the Linux user service. |

Use `autoclaw <command> --help` for exact options. Removed command families such as `onboard`, `doctor`, and `openclaw` are not compatibility aliases.

## Provider behavior

Codex and Claude are managed integrations. OpenClaw is an experimental, user-managed compatibility integration; it remains selectable and may be the default.

The first configured provider becomes the default when no default exists. Later configuration does not replace it silently. Use `autoclaw providers set-default <provider>`.

`providers status` is passive. `providers check` performs the explicit bounded diagnostic and never runs an agent task. Codex login and logout use its native CLI. Claude and OpenClaw return user-owned identity instructions rather than changing those products.

The HTTP API and browser console do not mutate provider configuration or identity.

## Configuration precedence

`--config` selects the TOML file for one command. Otherwise AutoClaw uses `AUTOCLAW_CONFIG`, then the platform default path.

For individual settings, explicit constructor values win, followed by `AUTOCLAW_*` environment values, TOML, file secrets, and built-in defaults. Nested environment names use `__`. AutoClaw does not load an implicit `.env` file.

The API host must be `127.0.0.1`, `localhost`, or `::1`. The default port is `18125`. SQLite is the default database. PostgreSQL requires its own non-system schema.
