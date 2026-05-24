# Phase 0 Runtime Normalization Reopen Canon-Fix Plan

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Purpose

Reopen runtime-normalization execution truth in canon without touching app code or redesign owner docs. Supersede the older phase45 reopen/master chain as live routing authority, create the new summary-only master router, legalize one later same-program command-surface addendum over `Makefile`, narrow runner orchestration, and matching current/execution docs without reclassifying that work as Phase 5B ownership, and repair stale replacement links plus stale deleted-test references across the owned execution/current-doc surfaces so `docs_freeze` can validate the current tree truthfully.

## Owned surfaces

- `AGENTS.md`
- `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/maps/redesign-code-landing-map.md`
- `docs/execution/plans/phase-0-runtime-normalization-reopen-canon-fix.md`
- `docs/execution/evidence/phase-0-runtime-normalization-reopen-canon-fix.md`
- `docs/execution/reviews/phase-0-runtime-normalization-reopen-canon-fix.md`
- `docs/execution/plans/phase-0-to-4.5-runtime-normalization-reopen-program.md`
- `docs/execution/evidence/phase-0-to-4.5-runtime-normalization-reopen-program.md`
- `docs/execution/reviews/phase-0-to-4.5-runtime-normalization-reopen-program.md`

## Allowed collateral surfaces

- the stronger current DB-backed current-doc collateral page named on the Phase 0 page only where that lane or the later bounded command-surface addendum must be described truthfully as current-behavior contrast

## Ordered work

1. Create the new summary-only master triplet under `phase-0-to-4.5-runtime-normalization-reopen-program`.
2. Create the new authoritative Phase 0 reopen triplet under `phase-0-runtime-normalization-reopen-canon-fix`.
3. Reclassify the older master, addendum, and phase45 reopen chains as historical summary-only material with truthful authoritative-replacement links.
4. Patch `AGENTS.md`, the owned Phase 0 page, and the owned execution maps so the runtime-normalization reopen program is the live routing truth, the older phase45 reopen chain is historical background only, and one later same-program command-surface addendum is explicitly legal without pretending Phase 5B owns it.
5. Repair stale replacement links and stale deleted-test references across the owned execution surfaces and the allowed current-doc collateral.
6. Run `./.venv/bin/python -m scripts.docs.docs_freeze.cli` once after integration.

## Expected outputs

- new summary-only master triplet
- new authoritative Phase 0 reopen triplet
- Phase 0 canon explicitly legalizes the later same-program command-surface addendum without transferring Phase 5B ownership
- phase pages, execution maps, root canon, and current-doc collateral aligned to the new runtime-normalization reopen program

## Validators

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`

## Stop conditions

- stop if a truthful repair requires touching `apps/**`
- stop if a truthful repair requires touching `Makefile` or non-docs `scripts/**` in this slice instead of only legalizing the later addendum
- stop if a truthful repair requires touching `docs/redesign/**`
- stop if a truthful repair requires creating a fresh authoritative Phase 3, Phase 4A, Phase 4B, or Phase 4.5 triplet now

## Cross-links

- summary-only master plan:
  `../plans/phase-0-to-4.5-runtime-normalization-reopen-program.md`
- matching authoritative evidence:
  `../evidence/phase-0-runtime-normalization-reopen-canon-fix.md`
- matching authoritative review:
  `../reviews/phase-0-runtime-normalization-reopen-canon-fix.md`
