# Current CLI surface and config precedence

Status: Current

Last verified: 2026-05-12

This page defines the current CLI command families, important flags, and current config and env precedence.

## Current command groups

Current CLI parser in `apps/api/app/cli.py` exposes:

- `autoclaw init`
- `autoclaw serve`
- `autoclaw db upgrade`
- `autoclaw db reset`
- `autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]`
- `autoclaw definitions import [--overwrite reject|allow_new_revision]`
- `autoclaw task-compose start --file <task_compose_path>`
- `autoclaw service render`
- `autoclaw service install`
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

### Service

- `service render` prints a user service unit from the packaged template
- `service install` writes the env file and unit, then runs `systemctl --user` commands
- `service start` launches a detached local service without requiring systemd
- `service stop` stops that detached local service
- `service restart` restarts that detached local service
- `service status` reports detached local service pid, health, and log path

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

There is no shipped `up`, `doctor`, `config`, or `openclaw` root subcommand family in the current parser.

Current parser truth also excludes the redesign-target interaction flags:

- `--non-interactive`
- `--plain`
- `--no-color`

Those remain target CLI contract, not current shipped parser behavior in this checkout.

## Current config and override behavior

Current CLI uses a layered config, env, and flag model.

Important current behaviors include:

- config path can be overridden
- `AUTOCLAW_CONFIG` can redirect config loading
- explicit CLI flags override config-derived values for the active command
- SQLite path derives from the configured or default data dir
- `AUTOCLAW_*` env vars override TOML config through `app.config`
- init flags can supply data dir, DB URL, host, port, log level, and API keys
- service render/install use the resolved config, then allow `--data-dir` and `--env-file` overrides for unit generation
- service start/stop/restart/status use the resolved config and the configured data dir for local service state and logs

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
autoclaw db upgrade
autoclaw db reset --json
autoclaw definitions import --file ./reviewer.yaml --json
autoclaw definitions import
autoclaw task-compose start --file ./task-compose.yaml --json
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
