# 03 — Phase 3: Runtime and OpenClaw Integration

## Goal

Migrate the runtime kernel to the canonical execution model and keep OpenClaw delegation clean.

## In scope

- replace legacy `run` / top-level `attempt` ownership with `flow` / `node_attempt`
- move API thinking from run-scoped execution to flow-scoped execution
- persist node-attempt history and checkpoint history
- preserve version provenance through compiled-plan lineage
- keep OpenClaw delegation explicit via `node_sessions`
- freeze `node_sessions` reuse semantics as per-node bindings with optional active-attempt linkage
- add policy-filtered shared context publication and node-specific context projection
- gate delegated execution on manifest acknowledgement instead of prompt wording alone

## Required schema migration work

- drop or deprecate `runs`
- drop or repurpose top-level `attempts`
- remove `flows.attempt_id`
- create `node_attempts`
- create `flows.seed_compiled_plan_id`
- create `flow_revisions`
- create `flows.active_flow_revision_id`
- add `node_checkpoints.node_attempt_id`
- move approvals to `flow_id` / `node_attempt_id` scope
- add `context_items` and `context_manifests`
- add `wait_reason = context` handling

## Out of scope for this phase

- full committee scheduling
- rich operator UX
- deep policy DSL expansion
- production-grade watchdog sophistication

## Success criteria

- a task starts a flow directly
- runnable work creates `node_attempts`
- checkpoints are attached to `node_attempt_id`
- approvals can target flow / node / node attempt
- session reuse is scoped per `flow_node`, not per retry attempt
- delegated nodes acknowledge a projected context manifest before execution begins
- OpenClaw execution remains outside AutoClaw runtime truth
