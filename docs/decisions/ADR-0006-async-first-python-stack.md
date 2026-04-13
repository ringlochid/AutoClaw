# ADR-0006 — Async-First Python Stack

- **Status:** Accepted
- **Date:** 2026-04-13

## Context

AutoClaw is a long-running orchestration/control-plane service that will increasingly integrate with external runtimes, APIs, and operator-facing surfaces.
Future development should not be boxed into a sync-only backend style.

## Decision

The backend will be async-first.
Use:

- FastAPI
- SQLAlchemy 2.0 async style
- Pydantic v2
- enum classes instead of `Literal` for enum-like domain values

## Consequences

- early code should be written with async service boundaries in mind
- database access uses async engine/session patterns
- runtime integrations fit more naturally with external async I/O
- maintainers must keep code style aligned and avoid mixed old/new framework patterns
