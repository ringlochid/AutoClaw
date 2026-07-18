# CLI surface and config precedence

This page defines the current CLI command families, important flags, and current config and env precedence.

## Current command groups

The shipped root CLI exposes:

- `autoclaw init`
- `autoclaw serve`
- `autoclaw onboard`
- `autoclaw configure`
- `autoclaw doctor`
- `autoclaw config path`
- `autoclaw config show`
- `autoclaw db upgrade`
- `autoclaw db reset`
- `autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]`
- `autoclaw definitions import [--overwrite reject|allow_new_revision]`
- `autoclaw task-compose start --file <task_compose_path>`
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

This list reflects the shipped CLI surface.

## Current command roles

### Init and local setup

- write config file
- generate API keys when needed
- create default directories
- seed packaged registry definitions
- optionally upgrade DB and ensure schema

### Serve

- `serve` runs the API through `uvicorn`
- `serve` fail-fast checks OpenClaw support before API startup
- `serve` is a foreground process and is not durable if the parent shell or TTY exits

### Onboard, configure, doctor, and config

- `onboard` is the current first-run command and now fail-fast checks OpenClaw support before writing local config, touching DB state, or installing the managed service, then reconciles the AutoClaw-owned OpenClaw integration slice
- `configure` is the current targeted re-entry command for local, runtime, service, definitions, web, or OpenClaw integration sections; `definitions` re-seeds the packaged registry defaults, `web` refreshes the default `console_origins` allowlist, `service` can persist an explicit local API `--port` override, and when the requested section includes OpenClaw or managed-service reconciliation it fail-fast checks OpenClaw support before local runtime or service work
- `doctor` checks local AutoClaw config, DB, packaged resources, managed-service visibility, and the AutoClaw-owned OpenClaw integration slice, with the OpenClaw integration check reported first; `--fix` now fail-fast checks OpenClaw support before local or wrapper repair
- `config path` prints the current resolved AutoClaw config path
- `config show` prints the current resolved config-shaped payload

### Service

- `service render` prints a user service unit from the packaged template
- on the current shipped checkout, the managed service implementation is Linux with `systemd --user`
- `service install` fail-fast checks OpenClaw support, validates that the chosen local API bind target is available, persists an explicit `--port` override when supplied, then writes the env file and unit and runs `systemctl --user` commands
- `service uninstall` removes the user unit and optionally removes the env file
- `service start|restart` fail-fast check OpenClaw support before operating on the managed `systemd --user` service; `stop|status` remain managed-service readbacks/actions rather than detached local pid-file behavior

### OpenClaw wrapper commands

- `openclaw check` reports the current support classification, selected worker/operator agent state, patched OpenClaw agent-profile state, OpenClaw-managed AutoClaw MCP server state, wrapper-state presence, and Gateway compatibility without writing
- `openclaw setup` selects or bootstraps the worker/operator agent path for AutoClaw, patches those OpenClaw agent profiles, writes the OpenClaw-managed AutoClaw MCP server definitions, updates the local AutoClaw OpenClaw section, and rewrites the wrapper material under the AutoClaw data dir
- `openclaw doctor` checks integration drift across the worker/operator selection, the patched OpenClaw agent profiles, the OpenClaw-managed AutoClaw MCP server definitions, and the wrapper material; `--fix` rewrites only that AutoClaw-owned integration slice when the host shape is supported

### DB

- `db upgrade` ensures schema and seeds packaged definitions
- `db reset` recreates the shipped SQLite database path, then re-applies schema and seeds

### Definitions

- `definitions import --file ...` loads one local definition file and imports it through the guarded registry lifecycle
- zero-arg `definitions import` shallow-scans only top-level `*.yaml` files in the current working directory
- `--overwrite reject` is the default
- `--overwrite allow_new_revision` allows changed local content to create a new current revision through the existing registry write path

### Task compose

- `task-compose start --file ...` loads one local task-compose file and starts a task through the same backend task-start handler as `POST /tasks/start`

There is no shipped `up` root subcommand family in the current parser.

Current parser truth still excludes some richer presentation behaviors even though these flags now parse through the shared root shell:

- `--plain`
- `--no-color`
- `--verbose` on setup-style commands with nested command execution

`--non-interactive` already changes current command behavior on guided commands such as `onboard` and `configure`: it disables prompts and is required when those flows run without a TTY.

Those flags now run through the Click + Rich root shell with central parse and failure rendering, while the underlying command bodies still reuse the existing domain handlers.

## Current progress output contract

Mutating setup-style commands now emit concise human progress lines for major hidden phases. This covers `onboard`, `configure`, `doctor --fix`, `db upgrade`, `db reset`, `openclaw setup`, `openclaw doctor --fix`, and managed-service install/start/restart/stop paths.

Rules:

- Progress is operator-facing status, not machine payload.
- Progress is disabled for `--json` so command stdout remains parseable JSON for commands that emit JSON.
- Human progress reports config write/reuse, local bind checks, database schema work, packaged definition seeding, OpenClaw reconciliation, nested OpenClaw commands, service unit writes, and `systemctl --user` operations when those phases run.
- `--plain`, `--no-color`, `NO_COLOR`, and non-TTY output use stable ASCII status marks.
- TTY-rich output may use a small semantic icon set: DB, seed, OpenClaw, service, success, warning, and failure.
- Nested command labels are sanitized and do not print raw stdin payloads or JSON arguments containing tokens.
- Nested stdout/stderr is shown on failure and when `--verbose` is supplied; sensitive-looking token, password, authorization, and API-key values are redacted before rendering.

## Current config and override behavior

Current CLI uses a layered config, env, and flag model.

Important current behaviors include:

- config path can be overridden with `--config <path>` on shipped CLI commands
- `AUTOCLAW_CONFIG` can redirect config loading in service, shell, and integration contexts
- explicit CLI flags override config-derived values for the active command
- SQLite path derives from the configured or default data dir
- `AUTOCLAW_*` env vars override TOML config through the shared `autoclaw.config` settings loader
- init flags can supply data dir, DB URL, host, port, log level, and API keys
- OpenClaw flags and env can supply base URL, binary path, config path, token override, password override, worker agent id, and operator agent id
- `onboard`, `configure --section service`, and `service install` can persist an explicit local API `--port` override; the service-facing commands bind-check that target before writing managed-service state
- service render/install use the resolved config, then allow `--data-dir` and `--env-file` overrides for unit generation
- service start/stop/restart/status use the resolved config plus the managed service name and `systemctl --user`

Current commands rely on shared settings loading rather than each command hand-rolling config precedence.

## Current product defaults

Current defaults include:

- SQLite by default
- `127.0.0.1:18125` by default
- `platformdirs`-derived config and data directories by default
- non-test envs require an operator API key

## Current config file shape

Current shipped config is controller/runtime-focused. It does not use a required `definitions_root`, and it does not need a user-facing `[app]` section.

The minimal file written by `autoclaw init` now includes:

```toml
[paths]
data_dir = "/home/ubuntu/.local/share/autoclaw"

[database]
url = "sqlite+aiosqlite:////home/ubuntu/.local/share/autoclaw/autoclaw.persistence"
echo = false

[server]
host = "127.0.0.1"
port = 18125
console_origins = [
  "http://127.0.0.1:5173",
  "http://localhost:5173",
  "http://127.0.0.1:4173",
  "http://localhost:4173",
]

[logging]
level = "WARNING"

[security]
api_key = "<generated secret>"

[openclaw]
base_url = "http://127.0.0.1:18789"
agent_id = "autoclaw-worker"
operator_agent_id = "autoclaw-operator"
timeout_ms = 120000

[runtime]
dispatch_launch_retry_initial_backoff_seconds = 1.0
dispatch_launch_retry_max_backoff_seconds = 30.0
watchdog_inactivity_timeout_seconds = 900
watchdog_same_attempt_replacement_limit = 2
```

The example above shows the config shape only. When `autoclaw init` generates a fresh config without an explicit key flag, it writes a generated API key rather than the literal placeholder string shown here.

Current onboard/setup behavior may additionally persist these optional `[openclaw]` fields to keep later service runs independent from transient shell env overrides:

- `binary_path`
- `config_path`
- `gateway_token` when explicitly supplied through AutoClaw config/env
- `gateway_password` when explicitly supplied through AutoClaw config/env

Current port ownership also matters:

- `server.port` is the AutoClaw API and MCP bind port stored in local `config.toml`
- the OpenClaw gateway port is stored through `openclaw.base_url` because the current shipped v1 path supports loopback (`127.0.0.1`) only

Current load behavior also matters:

- legacy `openclaw.account` keys are ignored on load
- runtime auth can still resolve from the persisted OpenClaw config path when the Gateway token/password lives in the OpenClaw config family instead of the AutoClaw TOML

## Minimal example

```text
autoclaw init
autoclaw serve
autoclaw onboard --json
autoclaw configure --section openclaw --json
autoclaw doctor --json
autoclaw config show --json
autoclaw db upgrade
autoclaw db reset --json
autoclaw definitions import --file ./reviewer.yaml --json
autoclaw definitions import
autoclaw task-compose start --file ./task-compose.yaml --json
autoclaw openclaw check --json
autoclaw service render
autoclaw service start
autoclaw service status
```

## Expanded example

```text
init
  -> choose config path and data dir
  -> write config.toml
  -> seed packaged registry definitions
  -> optionally upgrade DB

service install
  -> resolve config + data dir + env-file path
  -> render the packaged systemd template
  -> write the env file and user unit
  -> run `systemctl --user daemon-reload`, `enable`, and optional `restart`
```

## Related pages

- [Packaging, CLI, and install](packaging-cli-and-install.md)
- [Definition registry and publish lifecycle](../api/definition-registry-and-publish-lifecycle.md)
- [API route families and lane map](../api/api-surface-and-route-map.md)
