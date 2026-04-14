# ADR-0006: Async-First Python Stack

## Status

Accepted

## Decision

Use async services for checkpoints and scheduler decisions where IO dominates.
Keep transactional boundaries small and deterministic.
