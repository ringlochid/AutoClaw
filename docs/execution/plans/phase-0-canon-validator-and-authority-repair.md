# Phase 0 Execution-Record Prune-Hard Cleanup

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: Phase 0 docs-only execution-record cleanup with prune-hard historical-record policy
- slice type: edit
- owner: Codex
- date: 2026-05-13

## Goal

- rewrite the authoritative Phase 0 plan, evidence, and review so they describe
  this docs-only canon cleanup instead of the older merged validator and
  current-doc wave
- remove low-value historical execution-record ballast that no longer adds
  unique replacement-routing value
- update Phase 0-owned execution canon so historical summaries are retained
  only when they still provide unique routing value, otherwise deleted

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Locked surfaces

- owned execution canon:
  - `docs/execution/README.md`
  - `docs/execution/how-to/use-this-pack-for-implementation.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- owned execution records:
  - `docs/execution/plans/phase-0-canon-validator-and-authority-repair.md`
  - `docs/execution/evidence/phase-0-canon-validator-and-authority-repair.md`
  - `docs/execution/reviews/phase-0-canon-validator-and-authority-repair.md`
  - superseded Phase 0 and cross-phase summary-only history under
    `docs/execution/{plans,evidence,reviews}/`
- do not edit:
  - `scripts/docs/**`
  - `apps/**`
  - non-Phase-0 phase-scoped records for Phases 1-3
  - non-Phase-0 current docs

## Ordered work

1. rewrite the authoritative Phase 0 triplet so it records only this docs-only
   prune-hard cleanup
2. update Phase 0-owned execution canon to stop assuming retained repair-wave
   ballast
3. delete the superseded `phase-0-closeout-grammar-and-proof*` and
   `phase-0-3-layout-and-shim-removal-program*` families because the active
   phase-scoped replacements and shared router pages now cover their routing
   function directly
4. rerun docs-only validation and confirm no surviving Phase 0 history needs to
   remain

## Validation and stop conditions

- required validator:
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
- additional docs-only checks:
  - search the execution pack for any surviving references to deleted
    historical families or retained-ballast assumptions
- stop if `docs_freeze` now requires `scripts/docs/**` changes or if a truthful
  cleanup would require non-Phase-0 current-doc edits
- stop if the required validator remains blocked by non-Phase-0 phase-scoped
  records that this slice is not allowed to edit
