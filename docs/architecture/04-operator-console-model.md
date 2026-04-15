# Operator Console Model

## Primary runtime view

- task -> flow -> node
- active flow revision
- node state (`ready`, `running`, `waiting`, `paused`, `done`, `failed`)
- latest checkpoint + blocker per flow

## Current shipped console detail

- flow overview and node list
- pending approval list with resolution controls
- retryable-node list based on explicit retry boundaries
- replan submission from an explicit requester node / attempt boundary

## Broader operator drilldown model

These deeper views exist in the broader operator model and internal audit APIs, but are not all surfaced in the shipped console UI yet:

- flow revision history
- node attempt history
- checkpoint timeline
- approval trail
- delegated session binding (`node_sessions`)
- shared workspace/context items and their publish status
- context manifest / acknowledgement state before execution
- effective version provenance (workflow / role / policy / skill versions)

## Current shipped console controls

- continue / pause / cancel flow
- approval resolve
- request replan from an explicit requesting node / attempt boundary
- retry nodes that expose an explicit retry boundary by creating a new `node_attempt`

## Broader operator model controls

- soft-stop
- force checkpoint boundary when needed

## Guardrails

- do not expose raw transcript as source of truth
- operator decisions are explicit and auditable
- history should be readable from relational records, not inferred from chat logs
