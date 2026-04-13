# ADR-0002 — Deterministic Compiler, Hybrid Planner

- **Status:** Accepted
- **Date:** 2026-04-13

## Context

AutoClaw needs flexible planning, but flexible planning alone should not directly define executable runtime structure.

## Decision

Planning may be hybrid/agentic.
Compilation must be deterministic once definitions, patches, and versions are pinned.

## Consequences

- planners propose; compiler validates and lowers
- compile results should be reproducible and hashable
- invalid cycles and illegal transitions are caught before runtime
- debugging and rollback are simpler than transcript-driven orchestration
