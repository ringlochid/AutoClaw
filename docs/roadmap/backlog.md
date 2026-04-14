# Roadmap Backlog

## Priority 1

- full schema migration away from `runs` / top-level `attempts`
- add `flow_revisions` and `node_attempts`
- add `node_checkpoints.node_attempt_id`
- add `approvals.flow_id` and `approvals.node_attempt_id`
- add version provenance inspection queries

## Priority 2

- add runtime `flow_edges` joins and scheduler constraints
- add `node_sessions` lifecycle and reuse rules
- add `node_plan_revisions` with candidate/adopted flow revision linkage

## Priority 3

- add watchdog/progress event stream
- add operator console slices for subtree + lineage diff
- consider denormalized provenance caches only if profiling proves they are needed
