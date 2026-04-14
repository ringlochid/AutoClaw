# 06 — Phase 6: Advanced Hierarchy and Packs

## Goal

Deliver the max-complexity workflow target in a bounded, safe implementation.

See `../flows/06b-max-complexity-workflow-full.md` for the explicit target graph.

## In scope

- loop node ownership with depth and role caps
- subtree execution and dependency joins
- committee/parallel branch execution where intentional
- revision-safe inserted branches and dependency-set replacement via new revision snapshots
- version-safe execution across replanned revisions

## Core runtime tables by this phase

- `flows`
- `flow_revisions`
- `flow_nodes`
- `flow_edges`
- `node_attempts`
- `node_checkpoints`
- `approvals`
- `node_sessions`
- `node_plan_revisions`

## Exit criteria

The max-complexity example is complete when it can:

- execute with bounded retries,
- preserve node-attempt and revision history,
- surface effective workflow / role / policy / skill provenance,
- and recover safely through approval/replan boundaries.
