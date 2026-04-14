# Operator Console Model

## Primary runtime view

- task -> flow -> node
- active flow revision
- node state (`ready`, `running`, `waiting`, `paused`, `done`, `failed`)
- latest checkpoint + blocker per flow

## Drilldown view

- flow revision history
- node attempt history
- checkpoint timeline
- approval trail
- delegated session binding (`node_sessions`)
- shared workspace/context items and their publish status
- context manifest / acknowledgement state before execution
- effective version provenance (workflow / role / policy / skill versions)

## Controls

- pause / resume / soft-stop / cancel flow
- approval resolve
- request replan
- retry node by creating a new `node_attempt`
- force checkpoint boundary when needed

## Guardrails

- do not expose raw transcript as source of truth
- operator decisions are explicit and auditable
- history should be readable from relational records, not inferred from chat logs
