# AutoClaw Roadmap

This file is the **front door roadmap** for the project.

Keep it short, stable, and public-facing.
Detailed execution notes live under `docs/roadmap/`.

## North Star

Build AutoClaw as a framework for **long-running adaptive work**:
user-editable definitions compile into a normalized plan, the runtime executes through parent supervision and child loops, and the control plane keeps workflow truth in the database.

## Current Phase

**Phase 1 — Kernel and Data Model**

Repo/bootstrap groundwork is in place.
Current work should focus on the minimum kernel that proves the architecture end to end.

## Active Milestones

1. Add the initial SQLAlchemy models and Alembic migration.
2. Implement registry import/publish scaffolding for role/policy/workflow definitions.
3. Implement deterministic compiler v0 for one default workflow pack.
4. Implement runtime v0 for `task -> run -> attempt -> flow -> checkpoint`.
5. Add minimal API and operator visibility for run inspection and approvals.

## Cut Line / Not Yet

These are explicitly **not** phase-1 goals:

- advanced hierarchy as the default runtime assumption
- committee review logic
- a large policy DSL
- a broad workflow-pack library
- rich console polish
- aggressive optimization passes in the compiler

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

## Expansion Rule

Expand scope only when the current phase has:

1. a real implementation slice
2. explicit verification
3. a short test-drive / reality check
4. a clear reason to grow the surface area

## Working Notes

- `docs/roadmap/current.md` = what we are actively building now
- `docs/roadmap/backlog.md` = parking lot, not committed roadmap truth
