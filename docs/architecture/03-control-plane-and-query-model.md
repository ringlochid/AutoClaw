# Control Plane and Query Model

## Scope

This document defines the **canonical target contract** for runtime truth.

Legacy `runs` / top-level `attempts` are historical migration debt and are not part of the current runtime implementation.

---

## Immutable definition and compile tables

### `compiled_plans`

- `id`
- `workflow_version_id`
- `compiler_version`
- `plan_hash`
- `source_snapshot`

### `compiled_plan_nodes`

- `id`
- `compiled_plan_id`
- `node_key`
- `parent_node_key`
- `role_version_id`
- `policy_version_id`
- `mode`
- `order_index`
- `skill_bindings` (JSONB; each binding stores `skill_version_id`, runtime skill name, state, manifest summary, artifact/source metadata, and provenance)
- `effective_payload` (JSONB; merged node description, metadata, resource bindings, and provenance that runtime can consume without re-reading raw source definitions)

### `compiled_plan_edges`

- `id`
- `compiled_plan_id`
- `from_node_key`
- `to_node_key`
- `edge_kind`
- `condition_expr`
- `order_index`

These tables are immutable provenance anchors.

### Skill reference registry/read model (recommended target)

Current implementation already has `skill_registry` and `skill_versions` as the pin/provenance layer.
Recommended target shape:

#### `skill_registry`

- `id`
- `provider`
- `key`
- `source_uri`
- `description`

#### `skill_versions`

- `id`
- `skill_registry_id`
- `version_label`
- `status`
- `source_ref`
- `manifest` (parsed `SKILL.md` summary, not only raw seed input)
- `artifact_ref` nullable
- `artifact_sha256` nullable
- `published_at`

`manifest` should be strong enough to drive operator inspection and runtime dispatch:

- `runtime_name` (the exact OpenClaw skill `name`)
- `description`
- `user-invocable`
- `disable-model-invocation`
- selected `metadata.openclaw.*` fields such as `primaryEnv`, `requires`, and `install`

This remains a reference/pinning layer.
AutoClaw should not become the default owner of raw `SKILL.md`, `scripts/`, or `references/` behavior.

---

## Runtime truth tables (canonical target)

### `tasks`

- `id`, `title`, `status`, `input_payload`

Tasks remain the runtime truth for one concrete job.
A richer user-authored `TaskSpec` may be imported/exported as YAML or edited in the console, but execution should normalize that intent into DB-backed task rows and bindings rather than reading live YAML files at runtime.

### `workspace_roots`

Reusable or task-scoped editable file trees.

- `id`
- `scope` (`task|shared`)
- `key`
- `title`
- `storage_uri`
- `kind` (`repo|docs|mixed|generated`)
- `mode` (`snapshot|overlay|checkout|scratch`)
- `status`
- `content_hash`
- `last_indexed_at` nullable
- `metadata` (JSONB)

### `context_spaces`

Reusable or task-scoped knowledge/wiki spaces.

- `id`
- `scope` (`task|shared`)
- `key`
- `title`
- `storage_uri`
- `source_workspace_root_id` nullable
- `status`
- `content_hash`
- `last_indexed_at` nullable
- `metadata` (JSONB)

### `manifest_roots`

Task-owned **manifest artifact roots** for generated manifest files and related audit artifacts.

- `id`
- `task_id`
- `key`
- `storage_uri`
- `status`
- `metadata` (JSONB)

`manifest_roots` are storage-location metadata only.
The actual execution truth remains in `context_manifests` rows under `flow` / `flow_node` / `node_attempt`.
A file/object copy under a manifest artifact root may be required by policy or packaging, but the row remains the audit truth.

### `task_resource_bindings`

Bind tasks to their default or linked workspace/context/manifest roots.

- `id`
- `task_id`
- `binding_role` (`primary_workspace|reference_workspace|primary_context|reference_context|manifest_root`)
- `workspace_root_id` nullable
- `context_space_id` nullable
- `manifest_root_id` nullable
- `mode` (`use_existing|ensure_task_primary|ensure_task_root|clone_from|seed_from`)
- `read_only` nullable
- `required`
- `metadata` (JSONB)

Validation rule:

- explicit `use_existing` / `clone_from` references must resolve during task instantiation or replan validation, when the needed task-specific identifiers are known
- `ensure_task_primary` / `ensure_task_root` validate configuration shape first and are materialized at task bootstrap if absent

Cardinality and integrity rules should be explicit:

- exactly one target foreign key should be populated per row (`workspace_root_id`, `context_space_id`, or `manifest_root_id`)
- at most one `primary_workspace` binding per task
- at most one `primary_context` binding per task
- at most one `manifest_root` binding per task
- `manifest_root` bindings should always target `manifest_root_id`
- `clone_from` should reference an existing reusable source in `metadata` and produce a task-owned bound root after bootstrap

## Packaging/runtime support tables (recommended next target)

When backend side effects and runtime variants grow beyond the smallest local-first shape, add a thin logical packaging/runtime layer rather than spreading backend-specific state through the core orchestration tables.

These tables should support the runtime, not replace the runtime truth already carried by `tasks`, `flows`, `flow_revisions`, `flow_nodes`, `node_attempts`, `node_checkpoints`, `approvals`, and `context_manifests`.

### `task_composes`

Phase 12 should make `task_composes` the sole persisted packaging and launch-binding record.

Conceptual boundary:

- `workflows` are the reusable orchestration image: graph, role refs, skill refs, policy refs, and node defaults
- `task_composes` are the task-scoped launch image: the bound task snapshot, chosen workflow meaning, task-scoped resources/dependencies, and packaged launch metadata
- runtime execution state stays in `flows`, `flow_revisions`, `flow_nodes`, `node_attempts`, `node_sessions`, `approvals`, and `context_manifests`

`task_composes` should answer: given this task plus one compiled workflow meaning, what exact context, resources, and launch metadata were bound to make it runnable?

Recommended target fields:

- `id`
- `task_id`
- `compiled_plan_id` (or equivalent immutable workflow revision reference)
- `compose_hash`
- `task_snapshot` (JSONB; title/description/task metadata snapshot when reproducibility needs it)
- `resource_snapshot` (JSONB; bound workspace/context/manifest roots, dependencies, and other task-scoped bindings)
- `compose_payload` (JSONB; resolved materialization paths, packaged environment metadata, and other derived launch details)
- `created_at`
- `updated_at`
- `superseded_at` nullable

Recommended lifecycle rule:

- one compose snapshot aligns to one task plus one compiled workflow meaning
- retries reuse the same compose when task bindings and compiled workflow meaning are unchanged
- replans that only change internal flow topology may stay in flow revision history alone
- replans or task rebinding that change launch meaning or task-scoped bindings create a new compose instead of mutating the old snapshot in place

Launch-surface rule:

- public create/start should become task-compose centric, not workflow-start centric
- `TaskCreate` remains a thin task record shape, not the full runnable-task contract
- the public start contract should submit a task-scoped compose spec that binds task intent, workflow entrypoint, context URIs, required skills, and task-scoped resources before flow creation

Phase 12 cleanup note:

- drop `task_images`; fold their hash/snapshot data into `task_composes`
- drop `runtime_images`; the immutable execution contract already exists in `compiled_plans` / effective node payload
- drop persisted `runtime_containers`; assemble live runtime views from `node_sessions`, `flow_nodes`, `node_attempts`, and `context_manifests`
- do not treat session/runtime state as canonical workflow or compose truth
- only add a thin execution-lease table later if a real multi-backend/runtime-lifecycle need appears that cannot be served by the existing orchestration tables

### `flows`

A flow is the execution container for a task.

- `id`
- `task_id`
- `seed_compiled_plan_id`
- `active_flow_revision_id`
- `status` (`pending|running|blocked|paused|failed|succeeded|cancelled`)
- `execution_no` or equivalent operator-facing ordinal (optional but recommended)

`flows` should not store a separate current `workflow_version_id`.

- the original seed lineage comes from `seed_compiled_plan_id`
- the current effective lineage comes from `active_flow_revision_id -> flow_revisions.compiled_plan_id`

### `flow_revisions`

A flow revision is an adopted or candidate executable graph revision.

- `id`
- `flow_id`
- `revision_no`
- `compiled_plan_id`
- `parent_flow_revision_id` nullable
- `status` (`candidate|active|retired|aborted`)
- `reason`
- `source_patch_payload` (JSONB)
- `adopted_from_node_plan_revision_id` nullable
- `adopted_at`

Adoption rule:

- candidate adoption should compare-and-swap against the still-active base revision
- if the candidate validated against a stale base, adoption must fail rather than silently replacing newer runtime truth

### `flow_nodes`

A flow node is structural graph state, not attempt history.

- `id`
- `flow_id`
- `flow_revision_id`
- `source_compiled_plan_node_id` nullable
- `parent_flow_node_id` nullable
- `supersedes_flow_node_id` nullable
- `logical_node_key`
- `node_key`
- `node_path`
- `state` (`ready|running|waiting|paused|done|failed`)
- `order_index`
- `status_payload` (JSONB)

`flow_nodes` are a **full snapshot owned by one `flow_revision`**.
When a replan is adopted, the new revision materializes its own `flow_nodes` rows and keeps old rows for audit.
`logical_node_key` (or equivalent lineage key) should let operators query one logical node across revisions without heuristics.

### `flow_edges`

Runtime dependency constraints separate from ownership.

- `id`
- `flow_id`
- `flow_revision_id`
- `from_flow_node_id`
- `to_flow_node_id`
- `edge_kind`
- `condition_expr`

`flow_edges` are a **full snapshot owned by one `flow_revision`**.
Replans create a new candidate edge set under a new revision; prior rows remain intact for audit.

### `node_attempts`

Concrete execution history for one node.

- `id`
- `flow_id`
- `flow_revision_id`
- `flow_node_id`
- `number`
- `status` (`pending|running|blocked|failed|succeeded|cancelled|aborted`)
- `retry_of_node_attempt_id` nullable
- `failure_signature` nullable
- `started_at`
- `finished_at` nullable

Status semantics:

- `failed` = ran and ended unsuccessfully, including retryable failure
- `aborted` = stopped because control moved elsewhere (operator cancel, superseded revision, invalidated work)

### `node_checkpoints`

Typed control boundaries attached to one node attempt.

- `id`
- `flow_id`
- `flow_node_id`
- `node_attempt_id`
- `sequence_no`
- `status` (`green|retry|blocked|needs_approval`)
- `summary`
- `payload`
- `failure_signature` nullable
- `recommended_next_action`
- `wait_reason` nullable (`approval|dependency|watchdog|operator|context`)
- `created_at`

### `approvals`

Approval rows are flow-scoped, with optional node/attempt scope.

- `id`
- `flow_id`
- `flow_node_id` nullable
- `node_attempt_id` nullable
- `status` (`pending|approved|rejected|not_required|expired`)
- `reason`
- `request_payload`
- `resolution_payload`
- `requested_at`
- `resolved_at` nullable
- `resolved_by` nullable

### `node_sessions`

OpenClaw context bridge for delegated node work.

- `id`
- `flow_id`
- `flow_node_id`
- `node_attempt_id` nullable
- `provider_session_key`
- `status`
- `created_at`
- `last_seen_at` nullable
- `last_heartbeat_at` nullable
- `lease_expires_at` nullable
- `closed_reason` nullable
- `ended_at` nullable

Session lifecycle rule:

- primary binding scope is **per `flow_node`**, not per retry
- `node_attempt_id` is optional and points at the active attempt using that session
- retries may reuse the same session while node identity remains valid
- when a replan replaces that node in a new revision, detach/close the old session and create a new binding for the replacement node

Minimal transition rule:

- for the smallest implementation, `node_sessions` may continue to carry the first backend handle directly
- if richer multi-backend lease tracking is ever needed later, keep `node_sessions` as the controller-facing session identity and add a thin execution-lease/read-model layer rather than restoring the full image/container hierarchy by default

### `context_items`

Typed context metadata for task-shared, flow-shared, and private working context.

- `id`
- `task_id`
- `flow_id` nullable
- `flow_revision_id` nullable
- `flow_node_id` nullable
- `node_attempt_id` nullable
- `scope` (`task_shared|flow_shared|node_private|attempt_scratch`)
- `kind` (`fact|decision|summary|suggestion|note|artifact|log`)
- `visibility_policy`
- `status` (`draft|published|superseded|archived`)
- `title`
- `storage_uri`
- `content_hash`
- `published_by`
- `source_checkpoint_id` nullable
- `published_at`

These rows are the metadata truth for shared/private context publication.
Curated long-lived wiki/knowledge content should live in `context_spaces`; `context_items` are runtime publication metadata, not an interchangeable second wiki store.
Filesystem or object-storage folders are materialized views over this metadata, not the only source of truth.

### `context_manifests`

Projected context slices for delegated node attempts.

- `id`
- `flow_id`
- `flow_node_id`
- `node_attempt_id`
- `node_session_id` nullable
- `manifest_root_id` nullable
- `manifest_no`
- `manifest_payload` (JSONB)
- `manifest_hash`
- `status` (`projected|acked|superseded|expired`)
- `projected_at`
- `acked_at` nullable
- `ack_checkpoint_id` nullable

`manifest_payload` should contain:

- required vs optional context items/paths
- resolved workspace mounts for the node attempt
- resolved context-space references or selected wiki paths
- hashes or version ids
- visibility/permission slice for the node
- execution phase (`bootstrap` before `execute`)
- node-local skill contract for bootstrap/execute (`required`, `allowed`, `blocked`, plus binding summaries with runtime names and pinned versions)

Ack semantics should be explicit:

- a manifest ack is a first-class runtime event bound to `manifest_hash`, `node_attempt_id`, and the delegated session identity
- unrelated checkpoints must not implicitly count as ack
- a new attempt or newly projected manifest always requires a fresh ack, even when the same `node_session` is reused
- acks become invalid when the manifest is superseded, the attempt is superseded, or the session binding is replaced
- timeout or lost-session conditions should transition the manifest/attempt into an explicit blocked or expired state rather than drifting silently

Required skill or resource materialization should be fail-closed:

- if a node declares a skill, workspace, or context dependency as `required`
- and the delegated session cannot materialize or verify it
- execution should block before the execute phase rather than silently degrading into prompt-only best effort

`context_manifests` rows are the audit truth.
A manifest file/object under a manifest artifact root is an optional or policy-driven materialized copy, not the canonical execution source of truth.

### `context_manifest_items`

Recommended relational expansion of projected item visibility for queryability, and effectively required once manifest-backed operator/audit queries are live.

- `id`
- `context_manifest_id`
- `context_item_id`
- `required`
- `order_index`

### `context_manifest_mounts`

Recommended relational expansion of resolved workspace/context mounts for queryability, and effectively required once manifest-backed operator/audit queries are live.

- `id`
- `context_manifest_id`
- `mount_kind` (`workspace|context_space`)
- `workspace_root_id` nullable
- `context_space_id` nullable
- `access_mode`
- `mount_role`
- `required`
- `order_index`

### `context_manifest_skills`

Recommended relational expansion of resolved skill requirements for queryability, and effectively required once manifest-backed operator/audit queries are live.

- `id`
- `context_manifest_id`
- `skill_version_id`
- `runtime_name`
- `state`
- `order_index`

Keeping the full JSON payload is still useful for replay/debug, but the most important visible/required slices should be queryable without JSON-only inspection.

### `node_plan_revisions`

Proposal ledger for structural change requests.

- `id`
- `flow_id`
- `requesting_flow_node_id`
- `requesting_node_attempt_id` required (the proposal must bind to a real requester attempt boundary)
- `base_flow_revision_id`
- `candidate_flow_revision_id` nullable
- `patch_payload`
- `reason`
- `status` (`proposed|validating|validated|rejected|adopted|superseded`)
- `error_text` nullable
- `created_at`
- `validated_at` nullable
- `adopted_at` nullable

Replan safety rules:

- candidate validation should bind to the `base_flow_revision_id` it was derived from
- candidate validation should also bind to the task-resource binding snapshot or equivalent task-binding freshness token it assumed
- adoption must fail if that base is no longer the active revision
- adoption should also fail if the task-resource assumptions used during validation are no longer current
- superseded in-flight attempts/sessions should transition to explicit terminal or detached states rather than remaining ambiguously active

---

## Minimum invariants and indexes

The architecture should document at least these invariants explicitly:

- `flow_revisions.revision_no` unique per `flow_id`
- at most one active `flow_revision` per `flow_id`
- `flow_nodes.node_key` unique per `flow_revision_id`
- `flow_nodes.logical_node_key` queryable/indexed for cross-revision lineage
- `node_attempts.number` unique per `flow_node_id`
- `node_checkpoints.sequence_no` unique per `node_attempt_id`
- at most one active `node_session` per live `flow_node_id`
- at most one current projected `context_manifest` per live `node_attempt_id` / active session binding scope
- `task_resource_bindings` uniqueness for primary task roots as described above, plus target exclusivity checks
- manifest ack lineage must reference exactly one projected manifest hash/attempt/session tuple

These invariants matter for retries, replans, operator audit, and stuck-state monitoring.

---

## History and provenance guarantees

The runtime must support these queries without transcript inspection:

### Flow history

- all revisions a flow has had
- which revision was active when a node attempt ran
- which patch/adoption changed the graph

### Node history

- all attempts for one concrete `flow_node_id` or one logical node lineage (`logical_node_key`)
- which checkpoint sequence happened within a specific attempt
- which approval blocked or released an attempt

### Context history

- which context items were published for a task or flow
- which manifest was projected to a node attempt
- whether the delegated session acknowledged the manifest before execution

### Resource history

- which workspace/context/manifest artifact roots were linked to a task
- whether a task used an explicit shared root or an auto-created task-owned primary root
- which flow revision and node attempt consumed which resolved mounts/refs
- whether a replan changed the effective resource binding set before adoption

### Version provenance

For any node attempt, derive the effective definition lineage by following:

1. `node_attempt.flow_revision_id`
2. `flow_revisions.compiled_plan_id`
3. `flow_nodes.source_compiled_plan_node_id`
4. `compiled_plan_nodes.role_version_id`
5. `compiled_plan_nodes.policy_version_id`
6. `compiled_plan_nodes.skill_bindings[*].skill_version_id`

This means we do **not** need to denormalize every version id onto `node_attempts` unless profiling later proves it necessary.

For the original flow seed lineage, use:

1. `flows.seed_compiled_plan_id`
2. `compiled_plans.workflow_version_id`

---

## Query slices

- **Current state:** `flows`, active `flow_revisions`, `flow_nodes`, current `node_sessions`
- **History / audit:** `node_attempts`, `node_checkpoints`, `approvals`, `node_plan_revisions`, `flow_revisions`
- **Structural snapshot:** `flow_nodes`, `flow_edges`
- **Context workspace:** `context_items`, `context_manifests`
- **Definition provenance:** `compiled_plans`, `compiled_plan_nodes`, `compiled_plan_edges`

---

## Scheduling truth

- ownership tree: `parent_flow_node_id`
- runtime dependency constraints: `flow_edges`
- checkpoint and approval events drive transitions
- approvals are first-class runtime truth, not ancillary notes
- delegated execution should start only after manifest projection + acknowledgement
- no scheduler decision should depend on raw transcript interpretation

---

## JSONB policy

Use JSONB only for flexible payloads (`status_payload`, checkpoint payloads, request/resolution blobs, patch payloads).

Identity, status, topology, lineage, and provenance stay relational and index-first.

Context payloads may still live in files/blobs, but publication state, visibility, manifest acknowledgement, and lineage should remain queryable from relational metadata.
If compiled-skill provenance queries become product-critical, add relational expansion or explicit indexes for compiled-node skill dependencies rather than relying on JSON-only scans of `compiled_plan_nodes.skill_bindings`.

---

## Migration note

The live implementation now uses the flow-first relational model.
Legacy `runs`, top-level `attempts`, `flows.attempt_id`, and `approvals.run_id/attempt_id`
should be treated as historical migration debt, not current schema.
