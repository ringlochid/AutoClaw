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
- build the next stage on the fresh schema baseline rather than adding compatibility shims
- avoid reintroducing compatibility surfaces that blur `flow` vs `run`

## Next stage

The next stage is controller-driven flow advancement and bounded implementation-loop semantics:

- add a thin controller-side `advance_flow_until_boundary(...)` helper so safe control transitions do not leave a flow accidentally idle
- make implementation-loop behavior explicit: retry budget, replan boundary, approval boundary, and success/sync exit conditions
- move variable control decisions into policy where they differ by workflow or node:
  - approval trigger/scope
  - post-approval behavior
  - retry/watchdog limits
  - sync/governance gates
  - runnable-node preference when multiple nodes are eligible
- add a minimum typed runtime/operator event surface for auditability and console timelines

## Explicitly not next stage

- no separate session-scoped active-state system parallel to `flow` / `flow_node` / `node_attempt`
- no new user-visible mode machine imported from external tooling
- no hook/plugin framework as the primary runtime control surface
- no transcript-driven control truth

## Implementation baseline

- fresh Alembic history starts at `apps/api/alembic/versions/20260414_0001_fresh_initial_schema.py`
- runtime API surface is flow-scoped (`/flows`)
- `continue_flow()` is the current advancement engine; some safe transitions still require another explicit continue step to keep the flow moving
- database verification should use the Docker-backed repo flow from `docs/roadmap/suggestion.md`

## Why this reset matters

This gives a cleaner model where:

- `flow` is the whole execution container
- `flow_revision` owns executable graph snapshots
- `node_attempt` is the execution container for one specific node
- history and provenance are queryable without transcript inspection
- shared context is published and projected through explicit runtime metadata, not hidden prompt residue
