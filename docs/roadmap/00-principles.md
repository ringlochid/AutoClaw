# 00 — Principles

## Goal

Keep AutoClaw controllable while it grows.

These rules are the project's early-stage guardrails.

## Architecture Principles

1. **Controller-first.**
   The control plane owns workflow truth. Workers and planners do not mutate truth directly.

2. **Database truth beats transcript truth.**
   Sessions help continuity, but live workflow state must be stored in DB tables and plan revisions.

3. **Deterministic compiler, hybrid planner.**
   Agentic logic may propose plan changes, but compilation/normalization/validation must be deterministic.

4. **Default path first.**
   The required kernel is `parent supervisor -> main execution loop child`.
   Bigger trees are extensions, not the default assumption.

5. **Loops are iteration state, not raw graph cycles.**
   Represent retry/repeat behavior explicitly through loop nodes and iteration records.

6. **Relational first, JSONB second.**
   Store structure, ownership, state, and version refs relationally.
   Use JSONB only for flexible payloads.

7. **Version and pin everything that affects execution.**
   Published definitions and skill refs must be pinned per run.

8. **OpenClaw owns skill packages.**
   AutoClaw references and pins skill bindings; it does not duplicate OpenClaw skill source by default.

9. **One page / one module / one concept should have one main job.**
   Avoid early boundary blur.

10. **Build real slices, then test-drive, then expand.**
    Avoid speculative surface-area growth before a real path works end to end.

## Product Principles

- Good fit: long-running adaptive workflows with supervision, retries, approvals, and replanning.
- Not primary fit: hard real-time control, massive fixed batch DAG execution, tiny one-shot tasks.

## Early-Phase Discipline

Before adding a subsystem, ask:

- Does the current phase actually require it?
- Does it tighten or blur the architecture?
- Can it wait until the first real vertical slice is verified?
