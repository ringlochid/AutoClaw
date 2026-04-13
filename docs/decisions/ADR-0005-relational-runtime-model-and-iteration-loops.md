# ADR-0005 — Relational Runtime Model and Iteration-Based Loops

- **Status:** Accepted
- **Date:** 2026-04-13

## Context

A naive runtime graph blob is hard to query, hard to mutate safely, and hard to show in a dashboard.
Raw graph cycles are also a poor representation of repeated work loops.

## Decision

Runtime structure should be relational-first.
Ownership and state should live in normal tables/columns.
Loops should be represented as iteration state and iteration records, not raw graph back-edges.

## Consequences

- easier subtree queries and operator views
- clearer recovery and audit trails
- less temptation to dump the whole workflow into one JSONB blob
- cleaner boundary between ownership tree and optional dependency edges
