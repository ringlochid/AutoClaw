# Flow 03 — Plan Patch and Safe Recompile

## Replan principle

- Runtime should never mutate the live graph shape directly during a node call.
- Structural changes are recorded as proposals.
- Proposals are validated and compiled into candidate flow revisions.
- Only an adopted flow revision becomes executable.

Current implementation note:

- `request_replan()` still performs proposal -> validate -> compile -> adopt in one call.
- The current patch payload is a full candidate graph snapshot (`nodes`, `edges`, optional `skill_bindings`), not an in-place row-by-row mutation of the live runtime graph.
- The active revision only changes after the candidate revision has compiled and materialized successfully.

---

## Required history tables

### `node_plan_revisions`

One row per structural change request:

- `id`
- `flow_id`
- `requesting_flow_node_id`
- `requesting_node_attempt_id` required (binds the proposal to a real requester attempt boundary)
- `base_flow_revision_id`
- `candidate_flow_revision_id` nullable
- `patch_payload`
- `reason`
- `status` (`proposed|validating|validated|rejected|adopted|superseded`)
- `error_text` nullable
- `created_at`, `validated_at`, `adopted_at`

### `flow_revisions`

One row per executable graph revision:

- `id`
- `flow_id`
- `revision_no`
- `compiled_plan_id`
- `parent_flow_revision_id` nullable
- `status` (`candidate|active|retired|aborted`)
- `source_patch_payload`
- `adopted_from_node_plan_revision_id` nullable
- `adopted_at`


Each `flow_revision` owns a **full snapshot** of its `flow_nodes` and `flow_edges`.
A candidate revision materializes complete graph rows; previous revision rows stay unchanged.

---

## Transition semantics

### Proposal

A proposal is acceptable only if:

- requester belongs to the current active flow
- requester attempt is an explicit current attempt boundary for that node
- patch scope is legal for the requester
- patch does not orphan parent/child ownership
- patch keeps the graph valid under dependency rules

### Validate

Validation checks:

- JSON shape validity
- graph/topology closure
- role/policy permissions for the requester
- rollback feasibility
- provenance continuity (`compiled_plan_id` and source node lineage remain reconstructable)
- compile-time source validity for the candidate graph (role/policy resolution plus workflow normalization/validation)

### Adopt

- compile produces a candidate `flow_revision`
- set that candidate to `active`
- retire the previous active revision
- materialize a full candidate snapshot of `flow_nodes` and `flow_edges` under the candidate revision
- switch `flows.active_flow_revision_id` to the adopted revision
- resume only from a checkpoint boundary

---

## Safety rules

If validation fails:

- proposal -> `rejected`
- active flow revision remains unchanged
- error stays visible for operator review

If adoption fails after candidate creation:

- failed candidate -> `aborted`
- last active revision remains executable
- operator can retry or supersede with a new proposal
