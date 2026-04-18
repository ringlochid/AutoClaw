# ADR-0005: Task-owned Resource Roots and Flow-owned Manifests

## Status

Proposed

## Decision

AutoClaw should keep durable task resources separate from runtime execution projections.

- tasks own durable workspace/context/manifest artifact roots
- flows and node attempts own generated manifests and delegated session bindings
- workflows own the primary resource intent and task bootstrap defaults
- roles may provide light reusable resource-profile hints only
- policies enforce visibility, writability, sharing, and publishback rules
- manifests are generated runtime artifacts, not hand-authored definition inputs

## Definitions

### Workspace root

A workspace root is an editable file tree used for code, artifacts, patches, and scratch work.
It may be task-scoped or shared.

### Context space

A context space is a reusable wiki/knowledge layer used for summaries, docs, facts, prior decisions, and other curated context.
It may be task-scoped or shared.

### Manifest artifact root

A manifest artifact root is a task-owned storage location for generated manifest files and related audit artifacts.
It is not itself the execution truth.

### Context manifest

A context manifest is a per-node/per-attempt runtime projection that records the exact visible workspace mounts, context references, skill bindings, hashes, and execution phase for delegated execution.

## Consequences

### 1. Source-of-truth split

Keep one rule everywhere:

- YAML or console forms may define user/workflow intent
- DB rows are runtime truth
- filesystem or object storage is materialization

AutoClaw should not treat raw YAML files as the live runtime source of truth for tasks, flows, or manifests.
Unless and until a dedicated persisted `TaskSpec` model exists, `TaskSpec` should be treated as an authoring/import-export shape or console projection over task rows, not as a second canonical runtime object.

### 2. Ownership split

Recommended responsibility boundaries:

- **workflow**: task bootstrap defaults, graph structure, node-local resource intent, skill references
- **role**: behavior/instructions plus light resource-profile hints
- **policy**: enforcement rules for visibility, writability, sharing, and publishback
- **task**: durable bindings to workspace/context/manifest artifact roots
- **flow/node attempt**: generated manifests, delegated sessions, runtime state

### 3. Validation and auto-create semantics

Explicit references must not silently autocreate.

Use two explicit phases:

- **definition compile validation** for reusable semantics and valid binding-mode shapes
- **task instantiation / replan validation** for task-known explicit refs and currently bound roots

Rules:

- `use_existing` and `clone_from` should resolve in the first phase where the needed task-specific identifier is actually known
- `ensure_task_primary` and `ensure_task_root` validate configuration shape at compile time and autocreate at task bootstrap if absent
- only `ensure_*` modes may autocreate durable task roots
- required skills or required resources must fail closed if runtime materialization/verification fails

This avoids typo-driven silent resource creation.

### 4. Replan semantics

Replans should preserve task-owned durable roots when possible.

- task-owned workspace/context/manifest artifact roots remain stable across retries and adopted replans unless the replan explicitly changes the binding target
- explicit new resource references introduced by a replan must validate before candidate adoption
- candidate adoption must fail on stale base revisions rather than silently replacing newer runtime truth
- autocreation of new durable roots should be limited to task bootstrap unless a later explicit operator-visible task rebinding flow is designed
- manifests regenerate for the new revision/attempt set
- prior manifests and node sessions remain auditable after replacement or retirement

### 5. Suggested default filesystem materialization layout

When a task-scoped resource is materialized onto a local filesystem, the default host path should come from the platform data dir rather than repo-relative folders or truncated task ids.

Recommended local-first layout:

- `<data_dir>/tasks/<full-task-id>/workspace/`
- `<data_dir>/tasks/<full-task-id>/context/`
- `<data_dir>/tasks/<full-task-id>/manifests/`

Rules:

- use the full task id (or another full canonical id), not an abbreviated prefix such as `task_<id5>`
- keep `workspace_roots.key`, `context_spaces.key`, and `manifest_roots.key` as stable logical identifiers in the DB; the filesystem path is only a materialization detail
- keep logical URIs such as `task://<task_id>/workspace`, `task://<task_id>/context`, and `task://<task_id>/manifests` as the runtime-facing reference even when a local filesystem copy exists
- treat the `manifests/` directory as an export/audit location only; `context_manifests` rows remain the execution truth
- shared reusable roots, if materialized locally, should live under a separate stable namespace such as `<data_dir>/shared/...`, not inside a task directory

Current implementation note:

- current runtime code creates DB-backed logical roots and URIs for task defaults; it does not require a host path like `~/autoclaw-tasks/task_<id5>`

### 6. Data-model direction

Recommended target tables and relationships:

- `workspace_roots`
- `context_spaces`
- `manifest_roots` (manifest artifact roots)
- `task_resource_bindings`
- `context_manifests` referencing the resolved runtime projection and optional `manifest_root_id`

`context_manifests` rows remain the audit truth.
Any serialized file/object copy under a manifest artifact root is a materialized view or policy-driven export, not the canonical runtime source of truth.

Compiled node truth should include effective resource intent in `compiled_plan_nodes.effective_payload` so runtime can dispatch without re-reading raw authoring definitions.
