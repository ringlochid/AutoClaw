# ADR-0001: Control-plane-first Runtime Truth

## Status

Accepted

## Context

Runtime decisions must be made from stable tables, not from raw model transcripts.

## Decision

Use explicit tables for:

- flow graph structure (`flows`, `flow_nodes`, `flow_edges`)
- current state (`flow_node_state`)
- session binding (`node_sessions`)
- adaptation (`node_plan_revisions`, `flow_revisions`)

Keep JSONB as payload extension only.
