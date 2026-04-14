# 05 — Phase 5: Replan, Watchdog, Approval, and Recovery Semantics

## Goal

Make blocked, failed, and adaptive execution safe and explicit.
This phase freezes recovery semantics so the system can replan and recover without losing auditability.

## In scope

- checkpoint semantics (`green`, `retry`, `blocked`, `needs_approval`)
- `wait_reason` semantics (`approval`, `dependency`, `watchdog`, `operator`, `context`)
- approval lifecycle at flow / node / node-attempt scope
- watchdog handling for stalled attempts
- structural replan ledger via `node_plan_revisions`
- proposal -> validate -> compile -> adopt -> activate-by-revision flow
- blocked-state recovery without transcript interpretation

## Required runtime records

- `node_plan_revisions`
- `flow_revisions`
- `flow_edges`
- `node_attempts`
- `node_checkpoints`
- `approvals`
- existing `context_manifests` when execution is blocked on context bootstrap

## Decisions that must be frozen before this phase closes

- after approval/context acknowledgement, does policy resume the same blocked attempt or create a new attempt?
- is `context_ack` represented only in manifest metadata, or also as a first-class checkpoint/event shape?

Do not leave these semantics implicit in implementation.

## Invariants

- every retry creates a new `node_attempt`
- every adopted graph change creates a new `flow_revision`
- topology changes do not happen in place
- every blocked/recovery path leaves an auditable trail
- no watchdog/approval/replan decision depends on raw transcript interpretation as the control truth

## Success criteria

- structural replan requests are auditable end-to-end
- blocked and approval states are recoverable without history loss
- watchdog wake/retry paths preserve revision and provenance context
- runtime recovery semantics are explicit enough to implement without hand-wavy prompt logic
