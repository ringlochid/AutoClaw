# AutoClaw Roadmap

Last verified: 2026-04-20

This file is the front-door roadmap for the project.
Keep it short, stable, and honest.
Detailed migration planning lives under `docs/roadmap/`.

## North Star

Build AutoClaw as a framework for long-running adaptive work:
published definitions compile into immutable plans, runtime materializes those plans as revisioned flow graphs, delegated execution runs through OpenClaw, and control truth stays in explicit runtime records.

## Current reality

The flow-first runtime reset has landed.
The codebase is now on the `task -> flow -> flow_revision -> flow_node -> node_attempt` model.

The OpenClaw bridge is materially working.

The current problem is not legacy runtime ownership anymore.
The current problem is follow-on cleanup on top of a stabilized baseline:
- task compose / launch-binding truth
- canonical runtime read truth
- readiness / dispatch / resumability ownership cleanup
- keeping docs and route surfaces aligned with the code that actually exists

This is a credible stabilized runtime baseline, not a fully settled runtime architecture.

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

**Runtime stabilization / Phase 13 carry-forward cleanup**

Current emphasis:

1. keep the already-landed controller advancement baseline honest
2. finish the remaining ownership cleanup around compose/resources/read paths
3. keep bounded-loop and governance work behind clear runtime ownership
4. keep operator/query surfaces and docs aligned with the code that actually exists

## What is explicitly not done yet

These are not the current implementation baseline:

- a fully cleaned runtime ownership model
- policy-driven sync/governance gates and bounded-loop behavior
- explicit bounded-loop policy for exit/retry/replan/approval semantics
- a fully closed migration/schema checkpoint gate

## Where to read next

- `docs/README.md` — documentation map and reading guide
- `docs/roadmap/current.md` — honest current state vs target
- `docs/refactor-checklist-runtime-stabilization.md` — completed runtime-stabilization closure record
- `docs/roadmap/00-principles.md` — invariants
- `docs/roadmap/suggestion.md` — engineering style, code placement, and verification guidance

## Working rule

Use `docs/roadmap/` as the real migration plan.
Keep this file as the short public-facing summary, not the place for drifting implementation notes.
