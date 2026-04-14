# AutoClaw Roadmap

This file is the front-door roadmap for the project.

Keep it short, stable, and public-facing.
Detailed execution notes live under `docs/roadmap/`.

## North Star

Build AutoClaw as a framework for long-running adaptive work:
user-editable definitions compile into immutable plans, the runtime executes those plans as flow graphs, and the control plane keeps workflow truth in the database.

## Current Phase

**Phase 3 — Runtime Model Reset and Migration**

The architecture is being realigned around the canonical execution model:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`

Legacy `run` / top-level `attempt` tables in the current codebase are now treated as migration debt, not target architecture.

## Active Milestones

1. Freeze the canonical runtime contract in docs and ADRs.
2. Migrate schema from `run -> attempt -> flow` to `task -> flow -> flow_revision -> flow_node -> node_attempt`.
3. Add runtime history and provenance for workflow / role / policy / skill versions.
4. Add revision-safe replan history (`node_plan_revisions`, `flow_revisions`).
5. Add scheduler-ready dependency/runtime tables (`flow_edges`, `node_sessions`).

## Cut Line / Not Yet

These are explicitly **not** the current implementation baseline:

- full committee-style multi-branch scheduling
- rich operator console polish
- broad workflow-pack library
- aggressive optimizer passes in the compiler

## Phase Index

- `docs/roadmap/00-principles.md`
- `docs/roadmap/01-phase-1-kernel-and-data-model.md`
- `docs/roadmap/02-phase-2-registry-and-compiler.md`
- `docs/roadmap/03-phase-3-runtime-and-openclaw-integration.md`
- `docs/roadmap/04-phase-4-operator-console.md`
- `docs/roadmap/05-phase-5-replan-watchdog-and-approval.md`
- `docs/roadmap/06-phase-6-advanced-hierarchy-and-packs.md`
- `docs/roadmap/current.md`
- `docs/roadmap/backlog.md`

## Working Notes

- `docs/roadmap/current.md` = what we are actively building now
- `docs/roadmap/backlog.md` = parking lot, not committed roadmap truth
