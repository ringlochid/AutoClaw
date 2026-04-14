# 06 — Phase 6: Advanced Hierarchy and Packs

## Goal

Deliver the max-complexity target workflow from AUTOCLAW_DESIGN_V2_1 in a bounded, safe implementation.

- The explicit target flow is documented in `../flows/06b-max-complexity-workflow-full.md`.

## In scope

- loop node ownership with depth and role caps
- subtree execution and dependency joins
- committee/parallel branch execution where intentional
- revision-safe replan that updates `flow_nodes` / `flow_edges`

## Core table set for phase 6

- `flows`
- `flow_nodes`
- `flow_node_state`
- `flow_edges`
- `node_attempts`
- `node_sessions`
- `node_checkpoints`
- `node_plan_revisions`
- `flow_revisions`
- `progress_events`

## Exit criteria

Phase 6 completes when max-complexity example can run with bounded retries,
approval checkpoints, and reproducible revision transitions.
