# Task compose root binding and host placement

Status: Target

This page defines the exact root-binding and host-placement semantics for v1 task compose.

## Human-authored roots

Task compose may bind only:

- `workspace`
- `context`

Each may use:

- `ensure_task_default`
- `ensure_host_path`
- `use_existing_host`

Semantics:

- `ensure_task_default` = controller-managed task-local authored root
- `ensure_host_path` = create if missing at explicit host path
- `use_existing_host` = fail if the explicit host path does not already exist

When an authored root binding is omitted, the single default-root rule is owned by [task-compose-schema](../workflows/task-compose-schema.md).

## Launch-bound placement facts

Successful `POST /tasks/start` creates exactly one immutable `TaskCompose` launch-binding record for that task run.

That binding freezes:

- the selected current workflow revision
- `workspace` placement
- `context` placement
- controller-owned placement of `outputs`, `tmp`, and `_runtime`

V1 rules:

- root placement is fixed at launch
- runtime structural CRUD, retry, checkpoint writes, redispatch, monitoring updates, and durable publication do not mutate or supersede `TaskCompose`
- no `TaskCompose` current/superseded family exists in v1

## Generated roots

The controller materializes these generated roots under the task folder:

- `outputs`
- `tmp`
- `_runtime`

They are not human-authored root bindings.

## Exact generated-root meanings

- `outputs/` controller-owned durable publication area, including `outputs/artifacts/`
- `tmp/` controller-owned transient carryover area, including `tmp/transfers/`
- `_runtime/` controller-owned runtime projections and monitoring surfaces

These generated roots are deterministic consequences of task start and runtime evolution, not authored placement choices.

## Host-placement rule

- Authored root binding controls where `workspace/` and `context/` live.
- Generated roots are placed under the task root the controller owns for that task.
- Generated roots are not rebound by runtime structural edits or retry.
- Surfaced refs are path-only in v1.
- If an external resource must be surfaced, runtime must localize it into `<task-root>/tmp/transfers/localized/` before surfacing it to agents.
- Runtime must not reuse a host-bound `context/` path as the surfaced localization destination just because `context` was authored outside the task root.

## Launch and regeneration boundary

After the launch commit succeeds, the controller regenerates only the projections backed by committed truth.

Required immediately after successful start:

- `_runtime/workflow-manifest.json`
- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.json`
- `_runtime/attempts/<attempt_id>/assignment.md`

These remain absent until their backing rows exist:

- `_runtime/attempts/<attempt_id>/latest-checkpoint.json`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
- `_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `_runtime/dispatch/<dispatch_id>/watchdog-state.json`
- `_runtime/dispatch/<dispatch_id>/provider-events.ndjson`

Additional rules:

- task start does not guarantee that a first dispatch has already been opened
- dispatch-local monitoring files appear only after a real `dispatch_id` and its backing rows exist
- structural adopt also follows commit-before-regenerate
- no generated projection becomes authoritative before the backing rows commit

## Truth rule

Generated files under `_runtime/` are useful shared projections, but they are not the runtime ground truth. Controller/DB state remains the final authority if a generated file lags or disagrees. Currentness is explicit in controller/DB truth and is never inferred from file order, timestamps, or which projection happened to be written last.

## Related contracts

- [Task root layout and generated files](task-root-layout-and-generated-files.md)
- [Filesystem layout and roots](filesystem-layout-and-roots.md)
- [Manifest contract](manifest-contract.md)
- [Task compose schema](../workflows/task-compose-schema.md)
