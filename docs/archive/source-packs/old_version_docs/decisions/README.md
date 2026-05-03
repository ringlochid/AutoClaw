# Architectural Decisions

Last verified: 2026-04-20

This folder stores ADRs for decisions that are still relevant to the current model.

## Current ADR set

- `ADR-0001-controller-first-db-truth.md` — control-plane-first runtime truth
- `ADR-0002-deterministic-compiler-hybrid-planner.md` — deterministic compiler and hybrid planner boundary
- `ADR-0003-parent-supervisor-main-loop-kernel.md` — delegation and parent/supervisor model
- `ADR-0004-openclaw-owns-skill-packages.md` — skill package ownership boundary
- `ADR-0005-relational-runtime-model-and-iteration-loops.md` — relational loop and iteration model
- `ADR-0006-async-first-python-stack.md` — async-first service/runtime stack
- `ADR-0007-task-owned-resource-roots-and-flow-owned-manifests.md` — task-owned durable roots vs flow-owned runtime manifests

## Guidance

- ADR numbers are unique and stable; use them as decision identifiers rather than assuming filename order alone.
- If an ADR is proposed rather than accepted, keep that status explicit in the document itself.
- If a current implementation change invalidates an ADR, either update the ADR or add a successor ADR instead of leaving silent drift.
