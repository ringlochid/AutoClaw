# Worker context contract

Status: Target

This page defines the canonical worker-facing read contract for the frozen v1 runtime.

V1 does not use a giant `WorkerContext` callback object that tries to inline the whole runtime database, prompt, planning state, boundary state, provider transport state, and writable-root policy in one payload.

V1 also does not use a canonical `GET /callback/current/context` reread route.

What survives is a smaller current-node read surface:

- one stable whole-workflow manifest
- one current assignment
- one latest checkpoint path when one exists
- the exact consumed durable refs that matter now
- optional explicit transient refs
- optional task-memory search hints

Assignment field ownership lives in [Assignment contract](assignment-contract.md). Checkpoint field ownership lives in [Checkpoint contract](checkpoint-contract.md).

Controller/DB state remains authoritative. The surfaced files below are deterministic controller-generated projections of that truth.

## Core rule

The current worker reads:

1. `_runtime/workflow-manifest.md`
2. current `_runtime/attempts/<attempt_id>/assignment.md`
3. current relevant `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
4. consumed durable refs surfaced in assignment
5. optional `transient_refs`
6. optional `task_memory_search_hints`, then direct search in `context/wiki/` and other curated docs under `context/`

The worker does not recover its context from:

- authored workflow-definition YAML
- flow/scope manifest splits
- `scope_key`
- provider continuity state
- dispatch-family callback enums
- callback read helpers
- callback credentials, env var names, or auth-file locations
- writable-root callback fields
- giant inline role/policy/system blocks

Concrete reading sequence:

1. open `_runtime/workflow-manifest.md` to understand where this node sits in the workflow
2. open the current `assignment.md` to see the exact `summary`, `instruction`, `criteria`, `consumes`, and `produces`
3. open `latest-checkpoint.md` only to understand what already happened and what should happen next
4. open each consumed durable ref by its surfaced `path`
5. inspect optional transient refs only if they help this assignment
6. search `context/wiki/` or other curated `context/` files only when the surfaced `task_memory_search_hints` suggest it

## Current worker read surface

There is no separately locked `worker_read_contract` API payload in v1.

The canonical worker context is the combination of:

- the stable manifest files under `_runtime/workflow-manifest.*`
- the current attempt-local `assignment.*`
- the current relevant `latest-checkpoint.*`
- surfaced durable refs from assignment or manifest
- optional surfaced `transient_refs`
- optional `task_memory_search_hints`

The prompt should surface the exact file paths and descriptions needed for that reread. Callback remains a write-only semantic lane.

If an implementation emits a convenience envelope around those already materialized files, treat it as a helper projection only, not as a second canonical runtime contract.

Illustrative convenience envelope only:

```yaml
worker_read_surface:
  current_node_key: string
  current_node_kind: root | parent | worker
  workflow_manifest_path: string
  assignment_path: string
  latest_checkpoint_path: string | null
  consumed_refs: [worker_consumed_ref, ...]
  transient_refs: [worker_transient_ref, ...] | optional
  task_memory_search_hints: [string, ...] | optional
```

Supporting shape:

```yaml
worker_checkpoint_ref:
  kind: checkpoint
  path: string
  description: string

worker_evidence_ref:
  kind: artifact | criteria | doc | wiki
  slot: string | null
  version: integer | null
  path: string
  description: string

worker_consumed_ref:
  one_of:
    - worker_checkpoint_ref
    - worker_evidence_ref

worker_transient_ref:
  kind: transient
  slot: null
  version: null
  path: string
  description: string
```

Rules:

- V1 surfaced refs are path-only.
- Runtime must localize any external resource into the task root before it is surfaced to the worker.
- any callback/session/dispatch binding identity stays internal to the runtime/gateway and is not part of the canonical worker read surface
- callback write authority is injected privately by the runtime/launcher and is not part of prompt-visible semantic context
- `workflow_manifest_path` points at the stable whole-workflow manifest.
- `assignment_path` points at the current deterministic assignment projection for this attempt.
- `latest_checkpoint_path` points at the current deterministic checkpoint projection when one exists for the current attempt or when an upstream checkpoint is intentionally surfaced for this worker decision.
- `worker_checkpoint_ref` is the worker-context alias for the shared `node_runtime_file_ref` family restricted to `kind: checkpoint`.
- `worker_evidence_ref` is the worker-context alias for the shared `evidence_ref` family restricted to `kind: artifact | criteria | doc | wiki`.
- `consumed_refs` should mirror the current assignment `consumes` set plus any additional surfaced criteria/checkpoint/doc refs that the worker must read now.
- `transient_refs` is optional explicit carryover only. It is not durable truth.
- `task_memory_search_hints` is optional search guidance only. It does not silently promote task memory into required consumes.

## Manifest, assignment, and checkpoint roles

### Manifest

The manifest is the worker's whole-workflow picture.

It tells the worker:

- what workflow it is inside
- what node is current
- how nodes relate
- what each node consumes, produces, and checks
- which stable roots and current files exist

The worker should not be told to recover this from authored YAML or from a scope-only digest.

### Assignment

The assignment is the worker's current mission contract.

The worker should expect the canonical assignment shape defined by [Assignment contract](assignment-contract.md).

At minimum, the worker reads:

- `summary`
- `instruction`
- runtime-resolved `criteria`
- runtime-resolved `consumes`
- `produces` requirements
- optional explicit `transient_refs`
- optional `task_memory_search_hints`

The assignment is forward-looking. It is not history.

### Checkpoint

The checkpoint is the worker's durable summary of what happened and what should happen next.

The worker should expect the canonical checkpoint shape defined by [Checkpoint contract](checkpoint-contract.md).

At minimum, the worker reads:

- `checkpoint_kind`
- `outcome`
- `handoff`
- optional runtime-resolved `produced_artifacts` derived from accepted reduced durable artifact claims
- optional explicit `transient_refs`
- optional `task_memory_search_hints`

The checkpoint is backward-looking handoff, not a provider trace log.

## Deterministic generated files

The worker-facing runtime file families should be:

```text
<task-root>/
  _runtime/
    workflow-manifest.json
    workflow-manifest.md
    attempts/
      <attempt_id>/
        assignment.json
        assignment.md
        latest-checkpoint.json
        latest-checkpoint.md
        artifact-index.json
        transient-index.json
```

Rules:

- `_runtime/workflow-manifest.*` is the stable whole-workflow contract.
- `_runtime/attempts/<attempt_id>/assignment.*` is the deterministic current assignment projection.
- `_runtime/attempts/<attempt_id>/latest-checkpoint.*` is the deterministic current checkpoint projection.
- `artifact-index.json` and `transient-index.json` are navigation aids, not replacement truth surfaces.
- `_runtime/dispatch/<dispatch_id>/delivery-state.json`, `continuity-state.json`, `watchdog-state.json`, and `provider-events.ndjson` are observability-only surfaces, not ordinary worker context.

Short rule of thumb:

- manifest answers "where am I in the workflow?"
- assignment answers "what do I need to do now?"
- checkpoint answers "what happened already and what should happen next?"
- surfaced artifact or criteria paths answer "what exact evidence or rules do I need to inspect?"
- callback answers "how do I publish semantic writes back to the controller?" and not "what should I read?"

## Task-memory rule

- `context/wiki/` contains curated task-memory wiki pages and synthesized task memory for this task.
- `context/criteria/` contains explicit criteria files.
- Other curated files under `context/` are source/reference material such as user docs, PDFs, screenshots, and notes.
- In v1, workers search these files directly by path.
- Vector database or embedding retrieval is a v2 enhancement, not a v1 dependency.

## What is not part of the live v1 worker context

Do not keep these as the canonical worker-facing model:

- `binding_id`
- `flow_key`
- `flow_revision_key`
- `flow_node_key`
- `attempt_key`
- flow/scope manifest split
- `scope_key`
- `current_boundary_summary`
- `parent_evidence_bundle_ref`
- `replan_scope_ref`
- dispatch-family callback enums
- callback auth token material
- callback env var names
- callback auth-file paths
- provider-facing retry/continuity fields
- `writable_roots`
- inline role/policy/system prose blocks as a machine callback schema

Those ideas either belong in controller/DB truth, prompt wording, parent/root control docs, registry/tool docs, or monitoring surfaces. They do not belong in the canonical worker read surface.

## Example convenience envelope

```yaml
worker_read_surface:
  current_node_key: implement_change
  current_node_kind: worker
  workflow_manifest_path: C:/tasks/task_2026_0042/_runtime/workflow-manifest.md
  assignment_path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_change.03/assignment.md
  latest_checkpoint_path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_change.03/latest-checkpoint.md
  consumed_refs:
    - kind: criteria
      slot: implement_change_delivery_criteria
      version: null
      path: C:/tasks/task_2026_0042/context/criteria/implement_change_delivery_criteria.v01.md
      description: Delivery criteria for the implement-change node.
    - kind: artifact
      slot: findings_report
      version: 1
      path: C:/tasks/task_2026_0042/outputs/artifacts/investigate_issue/findings_report/findings_report.v01.md
      description: Findings for downstream implementation.
  transient_refs:
    - kind: transient
      slot: null
      version: null
      path: C:/tasks/task_2026_0042/tmp/transfers/auth-refresh-repro-steps.md
      description: Optional transient repro notes surfaced for this assignment.
  task_memory_search_hints:
    - auth refresh screenshot
    - rollback fixture
```

## Related contracts

- [Manifest contract](manifest-contract.md)
- [Assignment contract](assignment-contract.md)
- [Checkpoint contract](checkpoint-contract.md)
- [Task root layout and generated files](task-root-layout-and-generated-files.md)
- [Runtime boundary and controller loop contract](runtime-boundary-and-controller-loop-contract.md)
- [Runtime database and object contract](runtime-database-and-object-contract.md)
- [Prompt contract](../prompt-layer/contract.md)
