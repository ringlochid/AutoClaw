# 04 — Phase 4: Operator Console

## Goal

Give operators useful execution visibility and explicit controls.

## In scope

- task/flow/leaf state summary
- checkpoint / approval history view
- pause / resume / cancel actions

## Data-model requirement for console

- cache-like `flow.status` for quick list views
- flow_node_state per node for local drilldown
- progress events for audit

## Design constraint

Do not expose raw session transcripts as control state.
Expose intent + state only.
