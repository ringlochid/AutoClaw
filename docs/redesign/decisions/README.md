# Redesign decisions

Status: Target

This surface holds the stable cross-cutting redesign decisions that deserve durable identifiers.

These ADRs are not a second architecture tree. They exist to answer:

- why the settled runtime model looks the way it does
- which earlier directions were rejected or demoted
- which cross-cutting invariants should survive future doc rewrites

Use the architecture pages for the detailed live contract. Use these ADRs for the durable rationale and the non-negotiable boundaries.

## Search-first routing

If you are asking:

- "Who owns runtime truth?" -> [ADR-0001-controller-first-relational-runtime-truth.md](ADR-0001-controller-first-relational-runtime-truth.md)
- "What does compiler still own, and what does runtime CRUD not own?" -> [ADR-0002-deterministic-compiler-and-immutable-compiled-plans.md](ADR-0002-deterministic-compiler-and-immutable-compiled-plans.md)
- "Why is the workflow tree-only and gate-era advancement removed?" -> [ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md](ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md)
- "What exactly is OpenClaw in the live model?" -> [ADR-0004-openclaw-adapter-normalization-and-worker-transport-boundary.md](ADR-0004-openclaw-adapter-normalization-and-worker-transport-boundary.md)
- "Why are task-root files projections instead of truth?" -> [ADR-0005-task-owned-roots-and-runtime-generated-projections.md](ADR-0005-task-owned-roots-and-runtime-generated-projections.md)
- "Why is runtime structural change adopt-based instead of in-place?" -> [ADR-0006-revision-safe-replan-and-adopt.md](ADR-0006-revision-safe-replan-and-adopt.md)

## Current accepted decision set

The current accepted set freezes:

- controller/DB-owned runtime truth
- launch-time compiler only
- tree-only authored workflow and explicit parent/root control tools
- OpenClaw as adapter normalization, not truth ownership
- deterministic task-root projections with path-only surfaced refs
- revision-safe structural adopt with validator + materializer/projector

- [ADR-0001-controller-first-relational-runtime-truth.md](ADR-0001-controller-first-relational-runtime-truth.md)
- [ADR-0002-deterministic-compiler-and-immutable-compiled-plans.md](ADR-0002-deterministic-compiler-and-immutable-compiled-plans.md)
- [ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md](ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md)
- [ADR-0004-openclaw-adapter-normalization-and-worker-transport-boundary.md](ADR-0004-openclaw-adapter-normalization-and-worker-transport-boundary.md)
- [ADR-0005-task-owned-roots-and-runtime-generated-projections.md](ADR-0005-task-owned-roots-and-runtime-generated-projections.md)
- [ADR-0006-revision-safe-replan-and-adopt.md](ADR-0006-revision-safe-replan-and-adopt.md)

## Historical reading rule

If another redesign page conflicts with an accepted ADR:

1. prefer the accepted ADR for the cross-cutting invariant it freezes
2. use the current owner page it points to for the concrete live contract detail
3. if those still disagree, treat that as canon drift and patch the owner page or ADR so the conflict disappears
