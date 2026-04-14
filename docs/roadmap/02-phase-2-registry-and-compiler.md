# 02 — Phase 2: Registry and Compiler

## Goal

Keep compiler deterministic and reject invalid definitions before execution.

## In scope

- published version selection for role/policy/workflow/skill
- graph validation and normalization
- compile output as immutable `compiled_plans`

## Outcome

- source and compiled artifacts are reliable and inspectable.

## Clarification

The compiler output feeds the runtime graph.
Runtime control still follows flow-first orchestration introduced in later phases.
