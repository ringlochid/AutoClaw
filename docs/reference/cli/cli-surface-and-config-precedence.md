# CLI surface and configuration precedence

The installed command is `autoclaw`. On a terminal, `init` and `setup` are guided. Add `--non-interactive` for scripts. Non-TTY and `--json` invocations do not prompt. Other commands are non-interactive unless a provider opens its own identity flow.

## Passive front door

Running `autoclaw` without a subcommand is the same as `autoclaw status`. It reads local config and provider selections only. It does not contact providers, inspect provider authentication, start a service, upgrade a database, or write files. JSON reports unchecked facts as `not_checked`; human output says that the view is local-only and points to the explicit check command.

## Command families

| Command | Shipped purpose |
| --- | --- |
| `autoclaw init` | Guide local config, then create or verify the exact current schema. |
| `autoclaw setup` | Guide primary/default provider setup, checking, supported login, and optional extra providers. |
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

Guided setup asks for the primary/default provider and explicitly selects it. Adding providers in that flow preserves the chosen primary. Direct `providers configure` sets the default only when none exists; later direct configuration preserves it. Use `autoclaw providers set-default <provider>` for an explicit direct change.

When Codex needs authentication, guided setup offers its native login flow and checks again. Claude and OpenClaw retain their user-managed identity instructions. Setup steps commit independently: cancellation preserves completed explicit steps, and rerunning reads current config rather than a setup journal.

`providers status` is passive. `providers check` performs the explicit bounded diagnostic and never runs an agent task. Human output says confirmed, failed, or not tested; JSON retains `passed`, `failed`, or `not_checked`. A ready result can still leave an axis not tested when the bounded check did not directly verify it. Codex login and logout use its native CLI. Claude and OpenClaw return user-owned identity instructions rather than changing those products.

Interactive setup and status use structured, colored terminal output. Redirected output and `NO_COLOR` remain readable plain text, and JSON is never decorated.

The HTTP API and browser console do not mutate provider configuration or identity.

## Configuration precedence

`--config` selects the TOML file for one command. Otherwise AutoClaw uses `AUTOCLAW_CONFIG`, then the platform default path.

For individual settings, explicit constructor values win, followed by `AUTOCLAW_*` environment values, TOML, file secrets, and built-in defaults. Nested environment names use `__`. AutoClaw does not load an implicit `.env` file.

The API host must be `127.0.0.1`, `localhost`, or `::1`. The default port is `18125`. SQLite is the default database. PostgreSQL requires its own non-system schema.
