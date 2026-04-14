# 01 — Phase 1: Registry Foundations and Compile Schema

## Goal

Lock the source registry and immutable compile contract.
This phase is about **definitions, versions, and compiled artifacts** — not the final runtime execution model.

## In scope

- role / policy / workflow / skill definition tables
- version lifecycle and published-version selection rules
- immutable `compiled_plans`, `compiled_plan_nodes`, and `compiled_plan_edges`
- plan hashing and source snapshot capture
- compile-time validation and normalization
- deterministic compile outputs from published inputs

## Remove misleading expectations from this phase

Phase 1 should **not** claim to deliver:

- the final flow-first runtime model
- `flow_revisions`, `node_attempts`, or approval/watchdog semantics
- OpenClaw session lifecycle rules
- shared-context bootstrap or manifest gating
- operator console behavior

If older notes imply “basic runtime persistence and execution bootstrap” as a stable target model here, remove that implication.

## Deliverables

- stable registry/version schema
- deterministic compiler contract
- immutable compile tables sufficient for later runtime materialization
- validation failures that stop bad definitions before runtime begins

## Out of scope

- `flows`, `flow_revisions`, `flow_nodes`, `node_attempts` as the canonical runtime target
- approval rows and checkpoint-driven recovery
- delegated session binding
- context publication / manifest projection

## Success criteria

- identical published inputs produce identical compiled output and plan hash
- invalid definitions fail before execution begins
- runtime can later seed execution from `compiled_plan_id` without consulting raw mutable source definitions
