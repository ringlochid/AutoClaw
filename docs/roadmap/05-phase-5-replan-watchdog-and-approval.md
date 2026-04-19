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

Baseline now established:

- after approval/context acknowledgement, the runtime currently resumes the same blocked attempt
- `context_ack` is currently represented through `context_manifests` rather than a separate checkpoint shape

Next-stage follow-up was identified here, but any still-open non-UI backend/runtime implementation work from that follow-up is now carried forward into **Phase 13**.

Historical follow-up items identified by this phase:

- decide which parts of post-approval behavior remain hardcoded invariants vs configurable policy
- decide whether minimum typed runtime/operator events should remain derived from existing records or gain a first-class event surface

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
