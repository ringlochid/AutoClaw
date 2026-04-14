# ADR-0001: Control-plane-first Runtime Truth

## Status

Accepted

## Context

Runtime decisions must be made from stable tables, not from raw model transcripts.

## Decision

Use explicit relational runtime truth for:

- execution container (`flows`)
- graph structure (`flow_revisions`, `flow_nodes`, `flow_edges`)
- execution history (`node_attempts`, `node_checkpoints`, `approvals`)
- delegated context binding (`node_sessions`)
- shared context metadata + bootstrap projection (`context_items`, `context_manifests`)
- adaptation (`node_plan_revisions`, `flow_revisions` lineage)
- compile provenance (`compiled_plans`, `compiled_plan_nodes`, `compiled_plan_edges`)

Keep JSONB as payload extension only.
