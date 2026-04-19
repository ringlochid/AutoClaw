# 03 — Phase 3: Runtime Reset and OpenClaw Integration

This phase remains historical. Any still-open non-UI backend/runtime work implied by this target runtime contract now belongs to **Phase 13**.

## Goal

Replace the legacy `run -> attempt -> flow` runtime with the canonical target model and make delegated execution explicit, auditable, and flow-scoped.

This is the phase that actually kills the misleading old runtime ownership model.

## Legacy removals and replacements

Replace these legacy structures:

- `runs`
- top-level `attempts`
- `flows.attempt_id`
- `approvals.run_id`
- `approvals.attempt_id`
- run-scoped runtime APIs/routes

With these target structures:

- `flows.task_id`
- `flows.seed_compiled_plan_id`
- `flows.active_flow_revision_id`
- `flow_revisions`
- `flow_nodes`
- `flow_edges`
- `node_attempts`
- `node_checkpoints.node_attempt_id`
- `approvals.flow_id` / `approvals.node_attempt_id`
- `node_sessions`
- `context_items`
- `context_manifests`

## In scope

- flow-scoped execution container (`flow`)
- revision-owned graph snapshots (`flow_revisions`, `flow_nodes`, `flow_edges`)
- per-node execution history (`node_attempts`)
- checkpoint history attached to a node attempt
- flow/node/node-attempt approval scope
- delegated execution binding via `node_sessions`
- policy-filtered shared context publication and manifest projection
- execution gating on manifest acknowledgement instead of prompt wording alone
- API thinking moved from run-scoped to flow-scoped operations

## Required schema migration work

- add `flows.task_id`, `flows.seed_compiled_plan_id`, `flows.active_flow_revision_id`
- create `flow_revisions`
- create revision-owned `flow_nodes` and `flow_edges`
- create `node_attempts`
- add `node_checkpoints.node_attempt_id`
- move approvals to `flow_id` / `node_attempt_id` scope
- create `node_sessions`
- create `context_items` and `context_manifests`
- add `wait_reason = context`
- stop treating `flow_nodes.iteration_index` or similar legacy fields as execution-history surrogates

## Recommended cutover sequence inside this phase

1. add new schema/tables alongside legacy runtime tables
2. materialize new flow-first runtime state from compiled output
3. switch checkpoint and approval writes to `node_attempt` scope
4. add `node_sessions` plus context-manifest bootstrap flow
5. switch service/API surfaces from `runs` to `flows`
6. stop writing legacy runtime ownership records
7. remove legacy tables/routes once no live code depends on them

## Out of scope for this phase

- rich operator UX polish
- committee scheduling and advanced hierarchy behavior
- production-grade watchdog sophistication
- pack authoring/productization

## Success criteria

- a task starts a `flow` directly
- every runnable execution slice creates a `node_attempt`
- checkpoints are attached to `node_attempt_id`
- approvals can target flow / node / node attempt
- session reuse is scoped per `flow_node`, not per retry attempt
- delegated nodes acknowledge a projected context manifest before execution begins
- OpenClaw remains the delegated execution engine, not the control-plane source of truth
