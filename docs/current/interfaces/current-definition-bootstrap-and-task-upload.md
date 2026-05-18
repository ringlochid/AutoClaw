# Current definition upload, bootstrap ingest, and task-root binding

Status: Current

Last verified: 2026-05-18

This page owns the current split between:

- public guarded definition upload plus registry bootstrap ingest
- task-root binding during runtime launch

They are not the same surface.

## Ownership rule

Use this page for the current split between:

- public definition upload and registry/bootstrap definition ingest
- task-root root binding and bootstrap placement under a task root

Use `definition-registry-and-publish-lifecycle.md` for current draft,
validate, publish, and registry lifecycle behavior.

## Current definition upload and registry bootstrap ingest

Current definition ingest has two current paths:

- guarded public upload through `POST /definitions`
- bootstrap seeding from packaged registry YAML

Current real implementation includes:

- packaged definitions under `app.resources`
- public guarded upload through the definition route family
- CLI- and DB-driven seeding through `seed_definition_registry(...)`
- runtime launch lookup against registry rows after seeding

The current tree still does not ship standalone supported import/export product
commands.

## Current task-root binding at launch

Current runtime launch uses `TaskComposeInput.roots` plus an explicit
`task_root` path.

Bootstrap persistence then resolves and stores bindings for workspace, context,
criteria, wiki, outputs, artifacts, tmp, transfers, runtime, attempts, and
dispatch roots.

This is current launch/bootstrap placement, not a public upload API.

## Current non-surface fact

The shipped router does not expose:

- `upload_task_file(...)`
- `POST /tasks/{task_id}/uploads`
- the older alias table for `workspace_docs`, `context_docs`, or
  `manifest_bundle`

Older docs that describe those upload surfaces are historical, not current.

## Current bootstrap path-safety rule

Current launch/bootstrap placement still enforces explicit root ownership:

- `TaskComposeInput.roots` may bind only the shipped `workspace` and `context`
  roots
- each root uses an explicit mode such as `ensure_task_default`,
  `ensure_host_path`, or `use_existing_host`
- the task-root resolver expands those bindings into `TaskRootPaths`
- runtime materialization stays under the resolved task-owned binding set

## Current result of launch bootstrap

Launch/bootstrap persists:

- task and task-compose rows
- task resource binding rows
- manifest-root and workspace-root rows
- compiled-plan and flow rows
- initial manifest, attempt, and dispatch projections

## Current write ownership

Current bootstrap placement is a controller-owned runtime-launch surface.

It is not equivalent to:

- registry publish
- public task upload
- operator-side file placement
- post-launch ad hoc manifest editing

## Minimal example

```text
definition ingest today
  -> `POST /definitions` for guarded operator upload
  -> or packaged definitions plus `autoclaw init` / `autoclaw db upgrade`
  -> registry rows become current truth

task-root placement today
  -> `TaskComposeInput.roots`
  -> explicit `task_root`
  -> launch/bootstrap persists resource bindings and materialized roots
```

## Expanded example

```text
launch bootstrap
  -> resolve `TaskComposeInput.roots`
  -> localize task-root paths
  -> persist task, task-compose, and binding rows
  -> materialize `_runtime/`, `workspace/`, `context/`, and `outputs/`
     support paths
```

## Evidence

- inspected code in `apps/api/app/api/routes/definitions.py`
- inspected code in `apps/api/app/registry/seeds.py`
- inspected code in `apps/api/app/cli.py`
- inspected code in `apps/api/app/runtime/launch/service.py`
- inspected code in `apps/api/app/runtime/launch/bootstrap/rows.py`
- inspected code in `apps/api/app/runtime/task_root/paths.py`
- inspected current route map in `api-surface-and-route-map.md`
- inspected tests in `apps/api/tests/helpers/runtime_seed.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_bootstrap.py`

## Related current pages

- `../architecture/task-roots-and-materialized-paths.md`
- `definition-and-task-compose-yaml-contract.md`
- `definition-registry-and-publish-lifecycle.md`
- `api-surface-and-route-map.md`

## Redesign pointer

For the target guarded-ingest and task-start contract, see
`../../redesign/interfaces/definition-ingest-and-upload-contract.md`.
