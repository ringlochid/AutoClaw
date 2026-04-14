# 04 — Phase 4: Operator Console

## Goal

Give operators useful visibility and controls over flows, revisions, nodes, and node attempts.

## In scope

- task/flow/node state summary
- active flow revision visibility
- node attempt history and checkpoint timeline
- approval queue and resolution controls
- pause / resume / cancel / retry actions

## Data-model expectations

- `flow.status` for list views
- `flow_nodes.state` for topology drilldown
- `node_attempts` for execution history
- `node_checkpoints` and `approvals` for operator evidence
- version provenance display from compiled plan lineage
