# Current manifest projection and acknowledgement

Status: Current

Last verified: 2026-04-24

This page defines what the current implementation means by a context manifest, how it is projected, and how acknowledgement works today.

## Current definition

Current manifests are controller-owned projected runtime slices created for delegated node attempts.

They are not:

- authored workflow input
- the full prompt contract
- the full worker bundle
- the primary truth for task roots

Current delegated execution is manifest-first and lineage-sensitive.

## Current truth source

Current manifest truth is the DB-backed `ContextManifest` row.

Current code also writes a materialized JSON file copy under the task manifests root, but that file is a generated copy, not the primary execution truth.

Current authoritative fields include:

- `manifest_no`
- `manifest_payload`
- `manifest_hash`
- `status`
- `projected_at`
- `acked_at`
- `ack_checkpoint_id`

These are implemented in `autoclaw-main/apps/api/app/db/models/runtime.py` and surfaced through runtime schemas in `autoclaw-main/apps/api/app/schemas/runtime.py`.

## Current payload shape

Current `project_context_manifest(...)` builds a payload that includes:

- `execution_phase`
- `required_items`
- `optional_items`
- `node`
  - `flow_node_id`
  - `node_key`
  - `node_path`
  - `mode`
- `task_defaults`
- `resources`

Current code also injects the materialized JSON path into the payload after writing the file copy.

Required manifest items may carry inline content when projection resolves it.

## Current lifecycle

Current status values implemented in code are:

- `projected`
- `acked`
- `superseded`

Current code does not yet expose the redesign's explicit `expired` status in `ContextManifestStatus`.

Lifecycle today is roughly:

1. controller creates a `projected` manifest for a node attempt
2. bootstrap dispatch tells the worker to acknowledge that manifest first
3. acknowledgement validates the binding and moves the manifest to `acked`
4. later projections for the same live scope supersede older projected manifests

## Current acknowledgement rule

Current acknowledgement is manifest-lineage-sensitive.

The worker must acknowledge using the exact:

- `manifest_id`
- `manifest_hash`
- delegated session identity

Current code validates that binding in `acknowledge_context_manifest(...)`.

When acknowledgement succeeds, current runtime:

- records `acked_at`
- creates or reuses an acknowledgement checkpoint
- sets `ack_checkpoint_id`
- moves the manifest status to `acked`

The acknowledgement checkpoint is a real `NodeCheckpoint` row with summary `context manifest acknowledged`.

## Current worker-facing shape

Current worker-facing manifest usage is split across:

- bootstrap dispatch text that includes projected manifest identity and payload
- later execution dispatch text that includes latest acknowledged manifest lineage
- worker bundle reads that expose current and recent manifests

Current code does not yet define a separate persisted markdown manifest view for workers.

## Current inspection surfaces

Current manifest inspection is mainly available through:

- worker bundle
- flow audit
- runtime read models that include current and recent manifest data

Current code does not yet expose a dedicated standalone manifest-query surface or target-style decomposed manifest item and mount slices.

## Minimal example

```text
controller
  -> project_context_manifest(...)
  -> ContextManifest row status=projected
  -> write generated JSON file copy

worker
  -> reads bootstrap dispatch
  -> ack_context_manifest(manifest_id, manifest_hash, session binding)

controller
  -> sets status=acked
  -> records ack_checkpoint_id
```

## Expanded example

```text
continue
  -> controller creates next blocked attempt
  -> controller projects a context manifest for that attempt
  -> worker receives bootstrap dispatch with manifest payload
  -> worker must ack before normal execution
  -> controller validates manifest hash plus delegated session binding
  -> controller records context manifest acknowledged checkpoint
  -> later execution dispatch and worker-bundle reads use the latest acknowledged lineage
```

## Evidence

- inspected code in `autoclaw-main/apps/api/app/runtime/dispatcher.py`
- inspected code in `autoclaw-main/apps/api/app/services/openclaw_bridge.py`
- inspected code in `autoclaw-main/apps/api/app/schemas/runtime.py`
- inspected code in `autoclaw-main/apps/api/app/db/models/runtime.py`

## Redesign pointer

For the target manifest, worker-context, and runtime-lineage contracts, see [Manifest contract](../../redesign/architecture/manifest-contract.md), [Worker context contract](../../redesign/architecture/worker-context-contract.md), [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md), and [Task root layout and generated files](../../redesign/architecture/task-root-layout-and-generated-files.md).
