# 03 — Phase 3: Runtime and OpenClaw Integration

## Goal

Execute compiled plans through the AutoClaw runtime while delegating actual agent work to OpenClaw.

## In Scope

- runtime instantiation from compiled plans
- parent supervisor + main loop child execution model
- OpenClaw adapter for session/task dispatch
- typed checkpoint ingestion
- basic retry / blocked / approval-aware transitions

## Out of Scope

- advanced subtree execution
- committees
- aggressive concurrency

## Deliverables

- runtime services for run start / continue / inspect
- OpenClaw integration wrapper
- checkpoint persistence path
- clear runtime state transitions

## Data Model Changes

- expand `flow_nodes`
- add any minimal session-link fields needed
- finalize status/state enums used in runtime

## API / Runtime Changes

- start run
- continue run
- pause/cancel placeholders
- inspect latest checkpoint

## Tests / Verification

- runtime can instantiate from compiled plan
- one parent + one child path works end to end
- blocked state persists cleanly
- OpenClaw adapter failures do not corrupt run state

## Exit Criteria

Phase 3 is done when a real compiled workflow can be executed through OpenClaw and persisted through at least one parent/child/checkpoint cycle.

## Deferred Follow-ups

- richer scheduling
- subtree supervisors
- dynamic plan patch adoption

## Risks

- letting OpenClaw transcript details leak into control-plane truth
- runtime state changes without proper DB ownership
