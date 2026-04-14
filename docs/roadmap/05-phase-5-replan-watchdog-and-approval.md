# 05 — Phase 5: Replan, Watchdog, and Approval

## Goal

Make adaptive execution safe when failures repeat or conditions change.

## In scope

- checkpoint-driven block/retry policies
- soft completion signals / confidence markers
- proposal/validate/adopt revision path
- approval gates for high-risk transitions
- scheduler wake and soft-stop flow controls

## Data model

- `node_checkpoints` records typed decision boundaries
- `node_plan_revisions` captures patch attempts
- `flow_edges` can be retired/inserted at adoption

## Success criteria

- replan history is auditable
- no hot-graph mutation during a node call
- blocked/running/error transitions are explicit and recoverable
