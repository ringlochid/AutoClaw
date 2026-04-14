# Roadmap Backlog

## Priority 1 (now)

- Add relational `flow_node_state` and `flow_edges` as first-class scheduling truth
- Add `node_sessions` bridge table for OpenClaw binding
- Add checkpoint-level state transitions and status reasoning
- Add schema migration from current table shape to target flow-first shape

## Priority 2

- Add `node_plan_revisions` and compile-adopt flow
- Add `flow_revisions` or equivalent acceptance ledger
- Add progress event stream for scheduler wake and audit

## Priority 3

- Add operator console slices for subtree and dependency joins
- Add deterministic runbook for max-complexity sequence
