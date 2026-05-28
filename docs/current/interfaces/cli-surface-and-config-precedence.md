# Current CLI surface and config precedence

Status: Current

Last verified: 2026-05-28

This page defines the current CLI command families, important flags, and current config and env precedence.

## Current command groups

Current CLI parser in `apps/api/app/cli.py` exposes:

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

Current docs must not imply a broader finished product CLI than this.

## Current command roles

### Init and local setup

- write config file
- generate API keys when needed
- create default directories
- seed packaged registry definitions
- optionally upgrade DB and ensure schema

### Serve

- `serve` runs the API through `uvicorn`
- `serve` is a foreground process and is not durable if the parent shell or TTY exits

### Onboard, configure, doctor, and config

- `onboard` is the current first-run command that can initialize local AutoClaw state and reconcile the AutoClaw-owned OpenClaw integration slice
- `configure` is the current targeted re-entry command for local, runtime, service, or OpenClaw integration sections
- `doctor` checks local AutoClaw config, DB, packaged resources, managed-service visibility, and the AutoClaw-owned OpenClaw integration slice; `--fix` repairs only those same owned surfaces
- `config path` prints the current resolved AutoClaw config path
- `config show` prints the current resolved config-shaped payload with secret redaction

### Service

- `service render` prints a user service unit from the packaged template
- on the current shipped checkout, the managed service implementation is Linux `systemd --user`
- `service install` writes the env file and unit, then runs `systemctl --user` commands
- `service uninstall` removes the user unit and optionally removes the env file
- `service start|stop|restart|status` operate on the managed `systemd --user` service instead of a detached local pid-file process

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

Current parser truth still excludes some redesign-target interaction behaviors even though the flags now parse:

- `--non-interactive`
- `--plain`
- `--no-color`

Those flags are accepted on the new operator-facing commands, but the full rich TTY UX contract still remains incomplete in this checkout.

## Current config and override behavior

Current CLI uses a layered config, env, and flag model.

Important current behaviors include:

- config path can be overridden
- `AUTOCLAW_CONFIG` can redirect config loading
- explicit CLI flags override config-derived values for the active command
- SQLite path derives from the configured or default data dir
- `AUTOCLAW_*` env vars override TOML config through `app.config`
- init flags can supply data dir, DB URL, host, port, log level, and API keys
- OpenClaw flags and env can supply base URL, binary path, config path, token override, password override, worker agent id, and operator agent id
- service render/install use the resolved config, then allow `--data-dir` and `--env-file` overrides for unit generation
- service start/stop/restart/status use the resolved config plus the managed service name and `systemctl --user`

Current commands rely on `_command_env(...)` and settings loading rather than each command hand-rolling config precedence.

## Current product defaults

Current defaults include:

- SQLite by default
- `127.0.0.1:8123` by default
- `platformdirs`-derived config and data directories by default
- non-test envs require public and internal API keys

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

## Evidence

- inspected code in `apps/api/app/cli.py`
- inspected code in `apps/api/autoclaw/cli.py`
- inspected code in `apps/api/app/config.py`
- inspected code in `apps/api/app/paths.py`
- inspected tests in `apps/api/tests/unit/test_cli.py`
- inspected current package manifest in `pyproject.toml`

## Related current pages

- `packaging-cli-and-install.md`
- `definition-registry-and-publish-lifecycle.md`
- `api-surface-and-route-map.md`

## Redesign pointer

For the clean-break target CLI groups and operator workflows, see `../../redesign/interfaces/cli-surface-and-operator-workflows.md` and `../../redesign/interfaces/api-surface-and-trust-lane-map.md`.
