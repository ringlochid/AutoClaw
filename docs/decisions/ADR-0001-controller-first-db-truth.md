# ADR-0001 — Controller-First, Database Truth

- **Status:** Accepted
- **Date:** 2026-04-13

## Context

AutoClaw coordinates long-running workflows that may span multiple sessions, tool calls, approvals, retries, and replans.
If the workflow truth lives only in agent transcripts or session state, recovery and audit become fragile.

## Decision

AutoClaw will be controller-first.
The control plane and database own workflow truth.
Agent sessions are helpful context containers, not the canonical source of orchestration truth.

## Consequences

- runtime state must be persisted explicitly
- approvals and checkpoints must be first-class records
- session history may improve continuity, but cannot replace DB state
- recovery and observability become tractable
