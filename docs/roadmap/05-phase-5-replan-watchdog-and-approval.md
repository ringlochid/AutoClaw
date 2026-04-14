# 05 — Phase 5: Replan, Watchdog, and Approval

## Goal

Make adaptive execution safe when failures repeat or conditions change.

## In scope

- typed checkpoint reasoning (`failure_signature`, `recommended_next_action`, `wait_reason`)
- approval gate lifecycle at flow/node/attempt scope
- proposal -> validate -> compile -> adopt replan pipeline
- candidate/active/retired flow revision tracking
- watchdog support for stalled node attempts

## Required tables

- `node_plan_revisions`
- `flow_revisions`
- `flow_edges`
- `node_attempts`
- `node_checkpoints`
- `approvals`

## Success criteria

- every structural replan request is auditable
- every node retry creates a new `node_attempt`
- every adopted graph change produces a new `flow_revision`
- blocked and approval states are recoverable without losing history
