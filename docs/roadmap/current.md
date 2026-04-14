# Current Roadmap Status

## Canonical target contract

The architecture now treats this as authoritative:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`

## Legacy migration debt in current code

Current implementation still contains legacy structures that should be removed or migrated:

- `runs`
- top-level `attempts`
- `flows.attempt_id`
- `approvals.run_id`
- `approvals.attempt_id`
- `current_attempt_number`

## Required schema adds / reshapes

- add `flows.task_id`, `flows.seed_compiled_plan_id`, `flows.active_flow_revision_id`
- add `flow_revisions`
- add `node_attempts`
- add `node_checkpoints.node_attempt_id`
- add `approvals.flow_id`, `approvals.node_attempt_id`
- add `flow_edges`, `node_sessions`, `node_plan_revisions`
- add `context_items` and `context_manifests`
- add `wait_reason = context` support for bootstrap/context gating
- move version provenance through flow seed lineage + active flow revision lineage

## Why this reset matters

This gives a cleaner model where:

- `flow` is the whole execution container
- `node_attempt` is the execution container for one specific node
- history and provenance are queryable without transcript inspection
- shared context is published and projected through explicit runtime metadata, not hidden prompt residue
- max-complexity workflow support does not depend on fake wrapper tables

## Where to read the target

- system overview: `docs/architecture/01-system-overview.md`
- control-plane model: `docs/architecture/03-control-plane-and-query-model.md`
- compact max-complexity summary: `docs/flows/06-max-complexity-workflow.md`
- exact target graph: `docs/flows/06b-max-complexity-workflow-full.md`
