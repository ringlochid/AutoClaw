# 04 — Phase 4: Operator Console and Read Models

## Goal

Give operators faithful visibility and control over the new flow-first runtime without inventing transcript-derived shadow state.

## In scope

- task / flow overview keyed by the canonical runtime model
- active flow revision visibility
- node state and node-attempt history
- checkpoint timeline and approval trail
- delegated session visibility (`node_sessions`)
- shared-context publish state and manifest acknowledgement state
- operator actions: pause / continue / cancel / retry / resolve approval / request replan

## Read-model rules

- list views should be keyed by `flow`, not legacy `run`
- drilldowns should read relational runtime truth, not reconstruct state from transcripts
- the console must not maintain its own competing source of truth
- context visibility should respect policy/role filtering, not expose every artifact by default

## Out of scope

- high-polish UI refinement
- advanced diff visualizations that are not needed for phase-4 operator correctness
- analytics/reporting layers that can be derived later

## Success criteria

- operators can see current flow state, active revision, and blockers without reading chat logs
- operators can inspect attempts, checkpoints, approvals, sessions, and context publication history
- operator actions map cleanly to runtime mutations already defined by the control-plane contract
