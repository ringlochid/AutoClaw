# ADR-0003 — Parent Supervisor + Main Loop Child as Kernel

- **Status:** Accepted
- **Date:** 2026-04-13

## Context

The framework can support larger subtrees and advanced packs, but making that the default would bloat the initial kernel and blur the main runtime contract.

## Decision

The minimum required runtime shape is:

`parent supervisor -> main execution loop child`

Reviewer/syncer/specialists remain extensions.
Larger trees remain advanced workflow packs.

## Consequences

- the default path stays understandable
- phase-1 implementation remains controllable
- advanced hierarchy can grow later without becoming the baseline assumption for every task
