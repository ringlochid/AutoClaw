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
- complete a short **Phase 6.5** stabilization pass before Phase 7 begins
- avoid reintroducing compatibility surfaces that blur `flow` vs `run`

## Current phase — 6.5

Phase 6.5 is the pre-Phase-7 stabilization and surface-cleanup pass.
See `06.5-phase-6.5-pre-phase-7-stabilization.md` for the full checklist.

Its must-fix scope is:

- tighten control integrity so stale or terminal attempts cannot mutate runtime truth
- centralize shared transition ownership before more controller logic lands
- freeze retry / watchdog / replan / resume semantics in one place
- clean the operator/public surface so it reflects the flow-first model rather than raw controller internals
- make the repo front door and doc indexes tell one honest current-state story
- add invariant tests for the control edges that Phase 7 will build on

## After Phase 6.5 — Phase 7

Phase 7 is controller-driven flow advancement and bounded implementation-loop semantics:

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
- runtime API surface is split into:
  - public/operator routes under `/flows` and approval resolution under `/approvals`
  - internal audit/control routes under `/internal/...`
  - public health under `/healthz`
- `/flows/{flow_id}/operator` is the compact operator summary
- `/internal/flows/{flow_id}/audit` is the full audit/debug view
- raw checkpoint/context-manifest/watchdog/compiler/bootstrap/internal approval-create routes are intentionally internal-only
- `continue_flow()` is the current advancement engine; some safe transitions still require another explicit continue step to keep the flow moving
- database verification should use the Docker-backed repo flow from `docs/roadmap/suggestion.md`

## Why this reset matters

This gives a cleaner model where:

- `flow` is the whole execution container
- `flow_revision` owns executable graph snapshots
- `node_attempt` is the execution container for one specific node
- history and provenance are queryable without transcript inspection
- shared context is published and projected through explicit runtime metadata, not hidden prompt residue
