# 04 — Phase 4: Operator Console

## Goal

Make the system observable and controllable without exposing too much internal complexity.

## In Scope

- task list / run list
- run detail view
- latest checkpoint view
- approval and blocker visibility
- minimal action controls: approve, reject, pause, resume, cancel

## Out of Scope

- polished graph visualization
- deep descendant tree explorer by default
- full analytics/telemetry suite

## Deliverables

- basic console routes/pages
- run summary UI
- node/checkpoint inspection basics
- approval action UI path

## Data Model Changes

- no large schema jump expected
- add only fields clearly needed for operator visibility

## API / Runtime Changes

- list tasks/runs
- run detail endpoint
- approval action endpoints
- status summary endpoint if needed

## Tests / Verification

- operator can see current run state
- operator can see latest checkpoint and blocker reason
- operator action updates state cleanly

## Exit Criteria

Phase 4 is done when the operator can understand what is running, what is blocked, and what needs attention without reading raw DB rows or transcripts.

## Deferred Follow-ups

- deep graph inspector
- advanced observability panels

## Risks

- exposing raw internal complexity too early
- building a UI that outruns the runtime's actual capabilities
