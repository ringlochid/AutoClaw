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
- `skill_bindings` (JSONB; each binding stores `skill_version_id` and manifest/source metadata)

### `compiled_plan_edges`

- `id`
- `compiled_plan_id`
- `from_node_key`
- `to_node_key`
- `edge_kind`
- `condition_expr`
- `order_index`

These tables are immutable provenance anchors.

---

## Runtime truth tables (canonical target)

### `tasks`

- `id`, `title`, `status`, `input_payload`

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

### `flow_nodes`

A flow node is structural graph state, not attempt history.

- `id`
- `flow_id`
- `flow_revision_id`
- `source_compiled_plan_node_id` nullable
- `parent_flow_node_id` nullable
- `node_key`
- `node_path`
- `state` (`ready|running|waiting|paused|done|failed`)
- `order_index`
- `status_payload` (JSONB)

`flow_nodes` are a **full snapshot owned by one `flow_revision`**.
When a replan is adopted, the new revision materializes its own `flow_nodes` rows and keeps old rows for audit.

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
- `ended_at` nullable

Session lifecycle rule:

- primary binding scope is **per `flow_node`**, not per retry
- `node_attempt_id` is optional and points at the active attempt using that session
- retries may reuse the same session while node identity remains valid
- when a replan replaces that node in a new revision, detach/close the old session and create a new binding for the replacement node

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

These rows are the metadata truth for shared/private context.
Filesystem or object-storage folders are materialized views over this metadata, not the only source of truth.

### `context_manifests`

Projected context slices for delegated node attempts.

- `id`
- `flow_id`
- `flow_node_id`
- `node_attempt_id`
- `node_session_id` nullable
- `manifest_no`
- `manifest_payload` (JSONB)
- `manifest_hash`
- `status` (`projected|acked|superseded`)
- `projected_at`
- `acked_at` nullable
- `ack_checkpoint_id` nullable

`manifest_payload` should contain:

- required vs optional context items/paths
- hashes or version ids
- visibility/permission slice for the node
- execution phase (`bootstrap` before `execute`)

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

---

## History and provenance guarantees

The runtime must support these queries without transcript inspection:

### Flow history

- all revisions a flow has had
- which revision was active when a node attempt ran
- which patch/adoption changed the graph

### Node history

- all attempts for a node
- which checkpoint sequence happened within a specific attempt
- which approval blocked or released an attempt

### Context history

- which context items were published for a task or flow
- which manifest was projected to a node attempt
- whether the delegated session acknowledged the manifest before execution

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
- delegated execution should start only after manifest projection + acknowledgement
- no scheduler decision should depend on raw transcript interpretation

---

## JSONB policy

Use JSONB only for flexible payloads (`status_payload`, checkpoint payloads, request/resolution blobs, patch payloads).

Identity, status, topology, lineage, and provenance stay relational and index-first.

Context payloads may still live in files/blobs, but publication state, visibility, manifest acknowledgement, and lineage should remain queryable from relational metadata.

---

## Migration note

The live implementation now uses the flow-first relational model.
Legacy `runs`, top-level `attempts`, `flows.attempt_id`, and `approvals.run_id/attempt_id`
should be treated as historical migration debt, not current schema.
