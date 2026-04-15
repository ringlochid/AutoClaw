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
- continue Phase 7 with controller-driven advancement and loop-governance hardening
- avoid reintroducing compatibility surfaces that blur `flow` vs `run`

## Current phase — 7 (controller-driven advancement, slice A)

Phase 7 has started.
See `07-phase-7-controller-driven-looping-and-governance.md` for the target plan and `06.5-phase-6.5-pre-phase-7-stabilization.md` for what already closed.

Its must-fix scope is:

- tighten control integrity so stale or terminal attempts cannot mutate runtime truth
- centralize shared transition ownership before more controller logic lands
- freeze retry / watchdog / replan / resume semantics in one place
- clean the operator/public surface so it reflects the flow-first model rather than raw controller internals
- make the repo front door and doc indexes tell one honest current-state story
- add invariant tests for the control edges that Phase 7 will build on

## Remaining Phase 7 work

- **implemented now**: `advance_flow_until_boundary(...)` and auto-advance hooks on safe mutation paths
  - checkpoint write (`green`, `retry`)
  - approval resolution
  - context-manifest acknowledgement
  - replan adoption
- **remaining**:
  - make implementation-loop behavior explicit: retry budget, replan boundary, approval boundary, and success/sync exit conditions
  - move variable control decisions into policy where they differ by workflow or node:
    - approval trigger/scope
    - post-approval behavior
    - retry/watchdog limits
    - sync/governance gates
    - runnable-node preference when multiple nodes are eligible
  - minimum typed runtime/operator event surface for auditability is partially in audit payload; richer console timeline semantics remain

## Explicitly not next stage

- no separate session-scoped active-state system parallel to `flow` / `flow_node` / `node_attempt`
- no new user-visible mode machine imported from external tooling
- no hook/plugin framework as the primary runtime control surface
- no transcript-driven control truth

## Implementation baseline

- fresh Alembic history starts at `apps/api/alembic/versions/20260414_0001_fresh_initial_schema.py`
- runtime API surface is split into:
  - public/operator routes under `/flows` and approval resolution under `/approvals`
  - internal audit/control routes under `/internal/...`
  - public health under `/healthz` and `/readyz`
- `AUTOCLAW_INTERNAL_API_KEY` is a superset credential today: it can call `/internal/...` and the public/operator routes; the console should still use the operator key by default
- `/flows/{flow_id}/operator` is the compact operator summary
- `/internal/flows/{flow_id}/audit` is the full audit/debug view
- raw checkpoint/context-manifest/watchdog/compiler/bootstrap/internal approval-create routes are intentionally internal-only
- `continue_flow()` is now a thin poll/invoke boundary for manual wakeups; safe transitions on major mutation paths auto-advance when possible
- database verification should use the Docker-backed repo flow from `docs/roadmap/suggestion.md`

## Why this reset matters

This gives a cleaner model where:

- `flow` is the whole execution container
- `flow_revision` owns executable graph snapshots
- `node_attempt` is the execution container for one specific node
- history and provenance are queryable without transcript inspection
- shared context is published and projected through explicit runtime metadata, not hidden prompt residue
