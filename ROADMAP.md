# AutoClaw Roadmap

This file is the front-door roadmap for the project.
Keep it short, stable, and honest.
Detailed migration planning lives under `docs/roadmap/`.

## North Star

Build AutoClaw as a framework for long-running adaptive work:
published definitions compile into immutable plans, runtime materializes those plans as revisioned flow graphs, delegated execution runs through OpenClaw, and control truth stays in explicit runtime records.

## Current reality

The **target docs are coherent**, but the **codebase is still on the legacy runtime model**.
Do not describe the current implementation as if the full flow-first reset has already landed.

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

**Phase 3 — Runtime Reset and OpenClaw Integration**

This phase is responsible for:

1. removing the legacy `run -> attempt -> flow` ownership model
2. moving runtime truth to flow / revision / node-attempt records
3. making approval/checkpoint/session state auditable
4. adding policy-filtered shared context publication and manifest-gated delegated execution

## What is explicitly not done yet

These are not the current implementation baseline:

- full flow-first API cutover
- rich operator console polish
- complete watchdog/replan semantics
- max-complexity hierarchy / packs

## Where to read next

- `docs/roadmap/current.md` — honest current state vs target
- `docs/roadmap/00-principles.md` — invariants
- `docs/roadmap/03-phase-3-runtime-and-openclaw-integration.md` — core migration phase
- `docs/roadmap/suggestion.md` — implementation order, code placement, style, and verification guidance

## Working rule

Use `docs/roadmap/` as the real migration plan.
Keep this file as the short public-facing summary, not the place for drifting implementation notes.
