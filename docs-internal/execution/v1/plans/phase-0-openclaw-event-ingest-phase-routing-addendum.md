# Phase 0 OpenClaw Event-Ingest Phase-Routing Addendum Plan

Status: Reference

selected phase: Phase 0
current phase page: docs-internal/execution/v1/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Purpose

Make the execution-canon ownership split explicit and truthful for the dispatch-scoped Gateway ingest seam that sits between the Phase 4A worker lane and the Phase 4B watchdog or support-state consumers.

## Phase-local role

- `P0-WP2`: patch the affected phase pages so the routing split is explicit instead of reconstructed from overlapping Phase 4 wording
- `P0-WP3`: patch the file lock map and design-code-landing map so execution routing, proof gates, and later closeout artifacts line up with the same ownership split

## Ordered work

1. Update the Phase 4A page so it explicitly owns the dispatch-scoped Gateway RPC transport and the immediate controller-owned per-dispatch ingest write seam.
2. Update the Phase 4B page so watchdog and support-state semantics are explicitly downstream consumers of committed truth rather than owners of raw transport or first-write behavior.
3. Update the Phase 4.5 page so authority collapse, prompt cleanup, and final ballast deletion are explicit follow-on work that consumes the already-landed Phase 4A and Phase 4B truths instead of reopening them.
4. Patch `docs-internal/execution/v1/maps/file-priority-map.md` and `docs-internal/execution/v1/maps/design-code-landing-map.md` so their ownership, collateral, and proof wording matches the same split.
5. Create the authoritative Phase 0 addendum triplet under the execution record homes with the exact execution-record grammar and validator outcomes.
6. Do not create a new summary-only master-program triplet unless routing truth actually lacks one; prefer the already-retained summary-only master-program records over adding new historical ballast.

## Validation

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `rg -n "dispatch-scoped|committed truth|ingest seam|summary-only: yes|Phase 4A owns|Phase 4B owns|Phase 4.5 owns" docs-internal/execution/v1/phases docs-internal/execution/v1/maps docs-internal/execution/v1/plans docs-internal/execution/v1/evidence docs-internal/execution/v1/reviews`
- `ruff check scripts/docs` and `mypy scripts/docs` only if `scripts/docs/*` changes

## Stop conditions

- stop if truthful completion requires edits under `apps/**`
- stop if truthful completion requires `docs-internal/current/v1/**` edits beyond direct replacement-link repair
- stop if truthful completion requires `docs-internal/design/v1/**` edits instead of execution-canon fixes
- stop if a new cross-phase summary artifact is needed to replace, rather than complement, an existing authoritative or summary-only execution chain
