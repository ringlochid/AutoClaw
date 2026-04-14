# Operator Console Model

## Primary runtime view

- task -> flow -> node
- node state (`running`, `blocked`, `done`, `failed`, `waiting_approval`)
- latest checkpoint and blocker

## Drilldown view

- checkpoint timeline
- session binding (`node_sessions`)
- active attempt history
- revision history

## Controls

- pause / resume / soft-stop / cancel
- approval resolve
- request replan
- retry node / force checkpoint boundary

## Guardrails

- do not expose raw transcript as source of truth
- operator decisions are explicit, not inferred from logs
