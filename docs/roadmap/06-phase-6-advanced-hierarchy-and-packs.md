# 06 — Phase 6: Advanced Hierarchy and Packs

## Goal

Deliver the max-complexity workflow target on top of an already-correct core runtime.
See `../flows/06b-max-complexity-workflow-full.md` for the target graph reference.

## Assumptions entering this phase

Before this phase starts, phases 3–5 should already have delivered:

- flow-first runtime ownership
- revision-safe graph snapshots
- node-attempt history
- approval/watchdog/replan semantics
- delegated session binding
- context bootstrap gating

Do not use phase 6 to paper over missing core runtime work.

## In scope

- loop/subgraph owners with explicit capability flags and depth caps
- cross-branch joins and dependency constraints
- committee/parallel branches where intentional
- revision-safe branch insertion via new `flow_revisions`
- version-safe execution across replanned revisions
- optional pack/template support built on the same runtime contract

## Guardrails

- do not invent wrapper entities that reintroduce `run`-style nesting
- do not let “packs” block hierarchy/runtime implementation if packaging details are still unsettled
- do not special-case advanced hierarchy outside `flow_revision` / `flow_node` / `node_attempt`

## Core runtime tables exercised by this phase

- `flows`
- `flow_revisions`
- `flow_nodes`
- `flow_edges`
- `node_attempts`
- `node_checkpoints`
- `approvals`
- `node_sessions`
- `node_plan_revisions`
- `context_manifests`

## Exit criteria

The max-complexity example is complete when it can:

- execute with bounded retries
- preserve node-attempt and revision history
- support delegated owner/pivot nodes as well as delegated leaves
- surface effective workflow / role / policy / skill provenance
- recover safely through approval, replan, watchdog, and context-bootstrap boundaries
