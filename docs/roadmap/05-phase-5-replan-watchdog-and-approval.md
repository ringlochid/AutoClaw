# 05 — Phase 5: Replan, Watchdog, and Approval

## Goal

Add controlled runtime adaptation and operational safety.

## In Scope

- structured plan patch schema
- plan revision persistence
- safe recompile boundaries
- watchdog health states and recovery ladder
- approval lifecycle hardening

## Out of Scope

- advanced optimizer passes
- free-form arbitrary graph mutation
- full multi-subtree orchestration

## Deliverables

- `node_plan_revisions` or equivalent
- plan patch validation path
- partial recompile trigger/adoption path
- watchdog state evaluation
- approval action lifecycle completion

## Data Model Changes

- plan revision tables/fields
- watchdog-related timestamps or counters if needed
- finalize approval lifecycle fields

## API / Runtime Changes

- submit patch proposal / replan path
- inspect revision history
- watchdog status visibility
- approval state transitions

## Tests / Verification

- safe boundary adoption works
- invalid patches are rejected cleanly
- repeated failure signatures can trigger watchdog logic
- approvals pause and resume correctly

## Exit Criteria

Phase 5 is done when AutoClaw can safely adapt the plan at checkpoints without mutating the runtime graph ad hoc.

## Deferred Follow-ups

- subtree-local replanning
- richer policy engine

## Risks

- patch model becoming too powerful too early
- watchdog logic creating false-positive churn
