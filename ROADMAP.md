# AutoClaw Roadmap

This file is the front-door roadmap for the project.
Keep it short, stable, and honest.
Detailed migration planning lives under `docs/roadmap/`.

## North Star

Build AutoClaw as a framework for long-running adaptive work:
published definitions compile into immutable plans, runtime materializes those plans as revisioned flow graphs, delegated execution runs through OpenClaw, and control truth stays in explicit runtime records.

## Current reality

The flow-first runtime reset has landed.
The codebase is now on the `task -> flow -> flow_revision -> flow_node -> node_attempt` model.

The current problem is no longer legacy runtime ownership.
The current problem is pre-Phase-7 stabilization: tightening control integrity, simplifying transition ownership, and cleaning the public/operator surface before controller-driven looping lands.

## Canonical target contract

The target execution chain is:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`

Supporting runtime records also include:

- `node_sessions`
- `context_items`
- `context_manifests`
- `node_plan_revisions`

Legacy `run` / top-level `attempt` tables in the current codebase are migration debt, not target architecture.

## Current phase

**Phase 6.5 — Pre-Phase-7 Stabilization and Surface Cleanup**

This phase is responsible for:

1. tightening current-attempt / current-revision guards on control writes
2. centralizing shared transition ownership before more controller logic lands
3. freezing retry / watchdog / replan / resume semantics in one place
4. cleaning the operator/public surface so it reflects the flow-first model
5. making the repo front door and indexes tell one honest current-state story

## What is explicitly not done yet

These are not the current implementation baseline:

- controller-driven advancement until boundary everywhere
- bounded implementation-loop semantics as one explicit runtime contract
- minimum typed runtime/operator event surface
- policy-driven governance before `sync`
- rich operator console polish

## Where to read next

- `docs/roadmap/current.md` — honest current state vs target
- `docs/roadmap/06.5-phase-6.5-pre-phase-7-stabilization.md` — the active pre-Phase-7 cleanup gate
- `docs/roadmap/07-phase-7-controller-driven-looping-and-governance.md` — the next phase after stabilization
- `docs/roadmap/00-principles.md` — invariants
- `docs/roadmap/suggestion.md` — engineering style, code placement, and verification guidance

## Working rule

Use `docs/roadmap/` as the real migration plan.
Keep this file as the short public-facing summary, not the place for drifting implementation notes.
