# Current task roots and materialized paths

Status: Current

Last verified: 2026-05-13

This page defines the current on-host task-root behavior and the current materialized path model.

## Current task-root owner

Current task roots are explicit launch inputs.

The runtime does not derive a task root from `platformdirs`. Instead, `launch_task_runtime()` receives an explicit `task_root`, and `resolve_task_root_paths()` expands that into the current task-root layout.

`platformdirs` still owns default config, data, state, and cache directories for the CLI, but not the per-task root path.

## Current root binding model

Current `TaskComposeInput.roots` can bind:

- `workspace`
- `context`

Current binding modes are:

- `ensure_task_default`
- `ensure_host_path`
- `use_existing_host`

Current binding behavior is:

- `ensure_task_default` -> use `<task_root>/<root_name>`
- `ensure_host_path` -> use `host_path` and create it if needed
- `use_existing_host` -> use `host_path`, but it must already exist

## Current materialized roots

Current code materializes these task-root paths:

- `workspace/` or the bound workspace host path
- `context/` or the bound context host path
- `context/criteria/`
- `context/wiki/`
- `outputs/`
- `outputs/artifacts/`
- `tmp/`
- `tmp/transfers/`
- `_runtime/`
- `_runtime/attempts/`
- `_runtime/dispatch/`

Current task-root layout is represented by `TaskRootPaths`.

## Current resource-binding model

Current runtime persists task resource bindings for:

- `workspace`
- `context`
- `criteria`
- `wiki`
- `outputs`
- `artifacts`
- `tmp`
- `transfers`
- `runtime`
- `attempts`
- `dispatch`

Those binding paths are written into `TaskResourceBindingModel` rows during bootstrap persistence.

## Current materialized files

Current materialization writes files such as:

- `_runtime/workflow-manifest.json`
- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.{json,md}`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.{json,md}` when present
- `_runtime/attempts/<attempt_id>/artifact-index.json`
- `_runtime/attempts/<attempt_id>/transient-index.json`
- `_runtime/dispatch/<dispatch_id>/prompt.md`
- `_runtime/dispatch/<dispatch_id>/prompt-request.json`
- `_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `_runtime/dispatch/<dispatch_id>/watchdog-state.json`
- `_runtime/dispatch/<dispatch_id>/provider-events.ndjson`
- `context/criteria/<slot>.vNN.md` plus compatibility `<slot>.md`
- `outputs/artifacts/<owner_node_key>/<slot>/current.json`

Current `_runtime/workflow-manifest.*` carries the live whole-workflow payload, including:

- `manifest_version`
- current filesystem roots
- `current_context.latest_checkpoint_path`
- `current_context.latest_relevant_checkpoint_path`
- top-level `structural_edit_palette`
- per-node `policy` when present

The markdown manifest may omit a rendered `Structural Edit Palette` section when both palette lists are empty, even though the machine payload still keeps the palette object. The stable manifest, attempt, and dispatch writers are synchronous post-commit helpers in the current shipped tree, so the taught task-root reread surfaces refresh before route success.

## Current workspace-lease rule

Current bootstrap persists a live workspace-root lease for a custom workspace host path.

That means:

- a live task can hold an `ensure_host_path` workspace root
- a second live task cannot reuse that same normalized workspace host path
- terminal flow closure releases the live lease

## Current dependency model

Current durable dependency sharing happens through:

- criteria files
- artifact publications and current-pointer rows
- surfaced exact current child artifact refs resolved from those current-pointer rows when a parent/root turn depends on child durable evidence
- controller-staged descendant checkpoint and artifact refs for release rereads when the relevant evidence reaches beyond the current direct-child set
- checkpoint refs
- assignment consumed refs
- manifest `current_relevant_paths`

Current code also keeps `latest_relevant_checkpoint_path` as a separate manifest field instead of asking readers to infer the parent/root handoff from `current_relevant_paths` ordering alone.

Current code does not ship the older manifest-root-only or context-item-only teaching model as the canonical dependency path.

## Minimal example

```text
<task_root>/
  workspace/
  context/
    criteria/
    wiki/
  outputs/
    artifacts/
  tmp/
    transfers/
  _runtime/
    workflow-manifest.md
    attempts/
    dispatch/
```

## Evidence

- inspected code in `apps/api/src/autoclaw/runtime/task_root/paths.py`
- inspected code in `apps/api/src/autoclaw/runtime/task_root/reads.py`
- inspected code in `apps/api/src/autoclaw/runtime/task_root/writes.py`
- inspected code in `apps/api/src/autoclaw/runtime/launch/bootstrap/projection.py`
- inspected code in `apps/api/src/autoclaw/runtime/launch/bootstrap/rows.py`
- inspected code in `apps/api/src/autoclaw/paths.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_bootstrap.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_attempt_files.py`
- inspected tests in `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
