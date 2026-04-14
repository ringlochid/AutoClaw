# Current Roadmap Status

## Status summary

The runtime reset has landed.
The codebase and target docs now align on the flow-first runtime model.

## Live contract

The current implementation treats this as authoritative:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`
- `node_sessions`
- `context_items`
- `context_manifests`

## Legacy status

These legacy structures are now historical, not live implementation:

- `runs`
- top-level `attempts`
- `flows.attempt_id`
- `approvals.run_id`
- `approvals.attempt_id`
- run-scoped routes / services
- `flow_nodes.iteration_index`-style execution-history modeling

## Current focus

- keep docs and examples aligned with the flow-first runtime
- build next-phase operator/runtime features on the fresh schema baseline
- avoid reintroducing compatibility surfaces that blur `flow` vs `run`

## Implementation baseline

- fresh Alembic history starts at `apps/api/alembic/versions/20260414_0001_fresh_initial_schema.py`
- runtime API surface is flow-scoped (`/flows`)
- database verification should use the Docker-backed repo flow from `docs/roadmap/suggestion.md`

## Why this reset matters

This gives a cleaner model where:

- `flow` is the whole execution container
- `flow_revision` owns executable graph snapshots
- `node_attempt` is the execution container for one specific node
- history and provenance are queryable without transcript inspection
- shared context is published and projected through explicit runtime metadata, not hidden prompt residue
