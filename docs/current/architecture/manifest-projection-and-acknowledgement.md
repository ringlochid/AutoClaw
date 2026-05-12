# Current manifest projection and acknowledgement

Status: Current

Last verified: 2026-05-12

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
- role and description
- declared consumes
- declared produces
- criteria slots and criteria file paths
- dependency fan-in and fan-out node keys

## Current lifecycle

Current manifest lifecycle is:

1. bootstrap launch resolves task-root paths, stages a durable
   `manifest_materialization` runtime effect, and returns after controller truth
   commits
2. the app-lifespan effect runner rematerializes the manifest after launch,
   checkpoints, boundary acceptance, retries, redispatches, or
   replan-driven structure changes
3. dispatch prompt building can also build a dispatch-scoped manifest view using
   the dispatch render timestamp as the current-relevant-path cutoff

Current manifest projection therefore follows runtime state changes, but it is
not itself the state owner.

Current `current_relevant_paths` may also surface exact current child artifact
refs as compact `kind: artifact` evidence refs when a parent/root turn depends
on child durable publications.
Current `latest_relevant_checkpoint_path` is no longer inferred from the full
surfaced checkpoint set; it follows the controller-selected checkpoint truth
already staged onto the current turn.
Current release rereads may also surface controller-staged descendant
checkpoint and artifact refs from `release_precondition_descendant_refs_json`
instead of rebuilding a direct-child-only view.

## Current timing rule

Manifest files are not a pre-return write-route requirement in the current
tree.

- runtime write routes commit controller rows and durable `runtime_effects`
  rows first
- the effect runner later drains manifest refresh work after return
- operator/runtime reads may surface the manifest file ref before the refreshed
  file body exists on disk
- GET routes do not recreate the manifest inline

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
  -> queue manifest refresh in runtime_effects
  -> commit controller truth + queued effect
  -> effect runner writes _runtime/workflow-manifest.json
  -> effect runner writes _runtime/workflow-manifest.md

later checkpoint or boundary
  -> update runtime rows
  -> queue manifest refresh in runtime_effects
  -> effect runner refreshes workflow-manifest files after return
```

## Evidence

- inspected code in `apps/api/app/runtime/projection/manifest_projection.py`
- inspected code in `apps/api/app/runtime/projection/manifest_materialization.py`
- inspected code in `apps/api/app/runtime/resources.py`
- inspected code in `apps/api/app/runtime/control/flows.py`
- inspected code in `apps/api/app/runtime/control/boundary.py`
- inspected code in `apps/api/app/runtime/post_commit.py`
- inspected code in `apps/api/app/runtime/launch/service.py`
- inspected tests in `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
- inspected tests in `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
