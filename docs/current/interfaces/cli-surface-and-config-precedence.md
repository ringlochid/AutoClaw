# Current CLI surface and config precedence

Status: Current

Last verified: 2026-04-25

This page defines the current CLI command families, important flags, and current config/env precedence.

## Current command groups

Current CLI parser in `autoclaw-main/apps/api/app/cli.py` exposes:

- `autoclaw init`
- `autoclaw serve`
- `autoclaw up`
- `autoclaw service install|start|stop|restart|status`
- `autoclaw db upgrade|bootstrap`
- `autoclaw doctor`
- `autoclaw config path|show`
- `autoclaw task-compose bootstrap|start`
- `autoclaw openclaw check`

Current docs must not imply a broader finished product CLI than this.

## Current command roles

### Init and local bootstrap

- write config file
- generate API keys when needed
- create default directories
- optionally bootstrap definitions
- optionally upgrade DB

### Serve and up

- `serve` runs the API and bundled console
- `up` is the convenience path that can also run DB upgrade first

### Service

- install user service unit
- start, stop, restart, and query service status

### DB and doctor

- DB upgrade and bootstrap
- doctor reports config, database, and definitions resource status

### Config and task compose

- show config path
- show effective config
- validate and start task-compose launch through the API

### OpenClaw check

- probe OpenClaw connectivity and current configuration

## Current config and override behavior

Current CLI uses a layered config/env/flag model.

Important current behaviors include:

- config path can be overridden
- `AUTOCLAW_CONFIG` can redirect config loading
- explicit CLI flags override config-derived values for the active command
- SQLite path can derive database URL
- definitions root, data dir, host, port, OpenClaw settings, log level, and API keys can all be supplied during init

Current commands rely on `_command_env(...)` and settings loading rather than each command hand-rolling config precedence.

## Current product defaults

Current defaults include:

- SQLite by default
- `127.0.0.1:8123` by default
- local OpenClaw base URL default
- non-test envs require public and internal API keys

## Minimal example

```text
autoclaw init
autoclaw up
autoclaw doctor
autoclaw task-compose start demo.yaml
autoclaw openclaw check
```

## Expanded example

```text
init
  -> choose config path and data dir
  -> write config.toml
  -> optionally bootstrap registry
  -> optionally upgrade DB

task-compose start
  -> read YAML file
  -> validate payload
  -> POST /tasks/composes/start with API key

doctor
  -> inspect config, database, and definitions resources
  -> report packaged vs configured definitions roots
```

## Evidence

- inspected code in `autoclaw-main/apps/api/app/cli.py`
- inspected tests in `autoclaw-main/apps/api/tests/unit/test_cli.py`
- inspected current package manifest in `autoclaw-main/pyproject.toml`

## Related current pages

- `packaging-cli-and-install.md`
- `definition-registry-and-publish-lifecycle.md`
- `api-surface-and-route-map.md`

## Redesign pointer

For the clean-break target CLI groups and operator workflows, see `../../redesign/interfaces/cli-surface-and-operator-workflows.md` and `../../redesign/interfaces/api-surface-and-trust-lane-map.md`.
