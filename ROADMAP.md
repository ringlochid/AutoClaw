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
The current problem is completing the remaining Phase 7 items: bounded loop contracts and policy-driven governance hooks after controller-driven auto-advancement is in place.

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

**Phase 7 — Controller-Driven Looping and Governance**

This phase is responsible for:

1. controller-driven advancement baseline now live on safe mutation paths (checkpoint/approval/manifest/replan auto-advance)
2. implementing bounded loop contracts (retry/replan/approval/exit)
3. adding policy-driven governance for sync and node control decisions
4. adding minimum typed runtime/operator event timelines
5. keeping the operator surface and docs aligned as these behaviors land

## What is explicitly not done yet

These are not the current implementation baseline:

- policy-driven sync/governance gates and bounded-loop behavior
- explicit bounded-loop policy for exit/retry/replan/approval semantics

## Where to read next

- `docs/roadmap/current.md` — honest current state vs target
- `docs/roadmap/06.5-phase-6.5-pre-phase-7-stabilization.md` — pre-Phase-7 stabilization closure record
- `docs/roadmap/07-phase-7-controller-driven-looping-and-governance.md` — remaining Phase 7 execution plan
- `docs/roadmap/00-principles.md` — invariants
- `docs/roadmap/suggestion.md` — engineering style, code placement, and verification guidance

## Working rule

Use `docs/roadmap/` as the real migration plan.
Keep this file as the short public-facing summary, not the place for drifting implementation notes.
