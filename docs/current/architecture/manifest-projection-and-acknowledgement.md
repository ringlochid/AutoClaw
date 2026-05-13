# Current manifest projection and acknowledgement

Status: Current

Last verified: 2026-05-13

Legacy filename retained for searchability.

This page defines the current workflow-manifest projection shipped by the
runtime and records that the older manifest-acknowledgement flow no longer
ships in the current tree.

## Current definition

Current manifests are whole-workflow runtime projections built from current
controller-owned state.

They are:

- generated from current task, flow, flow-node, assignment, attempt, and edge state
- materialized as JSON and Markdown under the task runtime root
- surfaced as task-scoped file refs from runtime and operator reads

They are not:

- an authored workflow input
- a separate callback acknowledgement object
- the primary runtime truth

## Current truth source

Current manifest truth comes from controller-owned runtime rows plus current
task-root bindings.

The materialized files are:

- `_runtime/workflow-manifest.json`
- `_runtime/workflow-manifest.md`

Those files are generated copies, not the primary execution truth.

Current code does not ship a separate acknowledged-manifest model or a
manifest-ack callback route.

## Current payload shape

Current `ManifestProjection` includes:

- `manifest_version`
- `active_flow_revision_id`
- `generated_at`
- `task`
  - `task_id`
  - `task_key`
  - `title`
  - `summary`
  - `instruction`
- `workflow`
  - `workflow_key`
  - `description`
- `filesystem_roots`
  - `workspace_path`
  - `context_path`
  - `outputs_path`
  - `tmp_path`
  - `runtime_path`
- `structural_edit_palette`
  - `roles`
  - `policies`
- `current_context`
  - `current_node_key`
  - `owner_node_key`
  - `active_attempt_id`
  - `active_assignment_path`
  - `latest_checkpoint_path`
  - `latest_relevant_checkpoint_path`
  - `current_relevant_paths`
- `node_tree`
- `dependency_index`

Current `node_tree` entries include:

- node key, parent/child keys, and node kind
- role, optional policy, and description
- declared consumes
- declared produces
- criteria slots and criteria file paths
- dependency fan-in and fan-out node keys

## Current lifecycle

Current manifest lifecycle is:

1. bootstrap launch resolves task-root paths, opens the root dispatch, commits
   controller truth, and then materializes the stable workflow-manifest inline
   before returning
2. the app-lifespan effect runner rematerializes the manifest after ordinary
   checkpoints, boundary acceptance, retries, redispatches, or
   replan-driven structure changes, and later backfills any queued dispatch
   projections after launch
3. dispatch prompt building can also build a dispatch-scoped manifest view using
   the dispatch render timestamp as the current-relevant-path cutoff

Current manifest projection therefore follows runtime state changes, but it is
not itself the state owner.

Current `current_relevant_paths` may also surface exact current child artifact
refs as compact `kind: artifact` evidence refs when a parent/root turn depends
on child durable publications.
Current `latest_relevant_checkpoint_path` is a dedicated manifest field
separate from `current_relevant_paths`.
When an open dispatch already carries `relevant_checkpoint_attempt_id`, the
projection uses that controller-selected attempt truth.
When no dispatch is open, the stable-manifest builder reuses the most recent
dispatch for the same attempt and carries forward its
`relevant_checkpoint_attempt_id` when one exists.
Prompt rendering itself consumes the projected
`latest_relevant_checkpoint_path` field and does not re-infer a checkpoint from
surfaced-ref list order.
Current release rereads may also surface controller-staged descendant
checkpoint and artifact refs from `release_precondition_descendant_refs_json`
instead of rebuilding a direct-child-only view.

## Current timing rule

Manifest timing is split by write surface in the current tree.

- launch now commits controller rows first and then materializes the stable
  workflow-manifest inline before return; queued dispatch projections still
  drain after return
- checkpoint, boundary, retry, redispatch, and ordinary runtime-effect
  refreshes still commit controller rows and durable `runtime_effects` rows
  first, then let the effect runner rewrite the stable manifest after return
- parent/root structural CRUD callback writes are stricter: parent/root tool
  calls register control-side stable-manifest sync, `commit_runtime_session()`
  rewrites the stable `_runtime/workflow-manifest.*` files against the
  in-flight controller state before the final commit, and success still means
  the taught reread path is already refreshed
- if that final structural-tool commit fails after the inline rewrite,
  `rollback_runtime_session()` rolls controller truth back and then makes a
  best-effort attempt to rematerialize the prior committed stable manifest
  before surfacing failure
- operator/runtime GET routes still surface the manifest file ref and do not
  recreate the manifest inline

## Current inspection surfaces

Current manifest inspection is available through:

- `workflow_manifest_ref` on runtime list/read responses
- `current_paths` on operator snapshot and trace responses
- prompt rendering, which points the current dispatch at the manifest markdown
  file

Current code does not ship:

- a separate manifest acknowledgement checkpoint
- manifest-lineage callback headers
- a worker-bundle manifest gate

## Minimal example

```text
launch
  -> build ManifestProjection from current runtime rows
  -> queue dispatch/runtime follow-up effects
  -> commit controller truth + queued effects
  -> write _runtime/workflow-manifest.json before return
  -> write _runtime/workflow-manifest.md before return

later checkpoint or boundary
  -> update runtime rows
  -> queue manifest refresh in runtime_effects
  -> effect runner refreshes workflow-manifest files after return

parent/root structural CRUD callback
  -> adopt the new structural revision/currentness
  -> queue manifest refresh in runtime_effects
  -> register control-side structural manifest sync
  -> rewrite stable manifest files from the in-flight controller state
  -> commit controller truth + queued effect
  -> on commit failure, rollback and rewrite the prior committed manifest
```

## Evidence

- inspected code in `apps/api/app/runtime/projection/manifest/projection.py`
- inspected code in `apps/api/app/runtime/projection/manifest/materialization.py`
- inspected code in `apps/api/app/runtime/projection/manifest/context.py`
- inspected code in `apps/api/app/runtime/projection/manifest/checkpoint_handoff.py`
- inspected code in `apps/api/app/runtime/task_root/paths.py`
- inspected code in `apps/api/app/runtime/control/flow/service.py`
- inspected code in `apps/api/app/runtime/control/parent_tools.py`
- inspected code in `apps/api/app/runtime/control/structural_manifest_sync.py`
- inspected code in `apps/api/app/runtime/effects/worker.py`
- inspected code in `apps/api/app/runtime/launch/persistence/runtime.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_manifest.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_manifest_checkpoint_handoff.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_replan_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_replan_descendant_cases.py`
- inspected tests in `apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py`
