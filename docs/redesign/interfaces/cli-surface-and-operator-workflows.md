# CLI surface and operator workflows

Status: Target

This page defines the frozen v1 root CLI surface.

The canonical CLI is aligned to the current shipped root-command model. Frozen v1 now makes one explicit exception for local definition import:

- `autoclaw definitions import ...`

## Canonical root command groups

- `autoclaw init`
- `autoclaw serve`
- `autoclaw up`
- `autoclaw doctor`
- `autoclaw config ...`
- `autoclaw db ...`
- `autoclaw definitions ...`
- `autoclaw task-compose ...`
- `autoclaw openclaw ...`
- `autoclaw service ...`

## Primary user-facing commands

- `autoclaw init`
- `autoclaw doctor`
- `autoclaw serve`
- `autoclaw db upgrade`
- `autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]`
- `autoclaw definitions import`
- `autoclaw task-compose start --file <task_compose_path>`

## Support and admin commands

- `autoclaw config path`
- `autoclaw config show`
- `autoclaw openclaw check`
- `autoclaw service install`
- `autoclaw service start`
- `autoclaw service stop`
- `autoclaw service restart`
- `autoclaw service status`

## Rule

Guarded definition upload remains the canonical API/plugin lifecycle surface. The frozen root CLI import surface is a local authoring front door over that registry truth rather than a replacement for it. Runtime flow control remains API/plugin-first and is not frozen as a root CLI command family here.

Task-start rule:

- `autoclaw task-compose start --file <task_compose_path>` reads one local YAML file
- that file must parse exactly as `TaskStartRequest`
- the CLI then submits that exact body to the same canonical backend task-start handler as `POST /tasks/start`
- launch concurrency and root-path conflict handling are backend concerns, not separate CLI semantics

CLI import rules:

- canonical definition files carry top-level `kind`, so the root CLI does not take `--kind`
- zero-arg `autoclaw definitions import` is a shallow current-working-directory scan only
- zero-arg import scans only top-level `*.yaml` files in the current working directory
- zero-arg import does not recurse into subdirectories
- zero-arg import does not scan a configured root or package-bundled root
- `--file` is the canonical explicit local import path
- bundle-manifest batch import, if retained in implementation, is compatibility/helper only rather than the primary frozen v1 authoring path

Removed from live canon:

- legacy directory/recursive definition-import variants

## Related contracts

- `cli-api-and-package-shape.md`
- `api-surface-and-trust-lane-map.md`
- `definition-ingest-and-upload-contract.md`
