# 02 — Phase 2: Deterministic Compiler and Runtime Handoff

## Goal

Make the compiler handoff strict, inspectable, and sufficient for runtime materialization.
This phase finishes the compiler-side contract before the runtime migration begins.

## In scope

- compiler consumes published versions only
- `compiled_plan_nodes` carry resolved role / policy / skill lineage
- `compiled_plan_edges` capture dependency/order constraints explicitly
- graph normalization and validation of node keys, ownership, references, and mode constraints
- compile inspection/debug surfaces keyed by `compiled_plan_id`
- deterministic diff/hash behavior for repeated compiles from equivalent inputs

## Remove misleading expectations from this phase

Phase 2 should **not** pretend to complete runtime migration.
It should not claim:

- flow-first API cutover
- `node_attempt` / checkpoint history
- `flow_revision` lifecycle
- approval/watchdog runtime semantics
- session/context bootstrap enforcement

## Deliverables

- compiled graph outputs that are complete enough to seed runtime state later
- explicit version provenance on compiled nodes
- validation strong enough that runtime does not need to re-interpret source definitions

## Runtime handoff contract

By the end of this phase, runtime should be able to assume:

- it receives a valid `compiled_plan_id`
- plan contents are immutable
- role / policy / skill lineage is already pinned
- graph structure is explicit in compiled tables

## Success criteria

- repeated compiles from the same published inputs are stable and inspectable
- bad graph/source definitions fail at compile time, not mid-execution
- phase 3 can materialize the new runtime from compiled output alone
