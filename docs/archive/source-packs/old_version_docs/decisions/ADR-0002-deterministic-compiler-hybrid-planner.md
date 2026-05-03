# ADR-0002: Deterministic Compiler, Hybrid Planner

## Status

Accepted

## Decision

- planner may reason and propose, but compiler output is deterministic for executable structure.
- compile-time decisions produce hashes and snapshots.
- runtime execution reads compiled plans, not raw intent text.
